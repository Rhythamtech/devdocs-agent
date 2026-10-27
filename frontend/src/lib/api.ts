const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/+$/, "")

/**
 * Resolve a docs endpoint for both deployment modes.
 *
 * Local dev talks to FastAPI directly through NEXT_PUBLIC_API_URL. Docker
 * builds leave it empty and proxy requests through the Next.js `/api/docs`
 * rewrite, so the browser never needs the internal `backend` hostname.
 */
export function docsApiUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`
  return `${API_BASE}${API_BASE ? normalized : `/api${normalized}`}`
}

interface ApiOptions {
  method?: string
  body?: unknown
  headers?: Record<string, string>
  token?: string | null
}

export interface UserProfile {
  id: string
  username: string
  email: string
}

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
  source?: "voice"
  toolCalls?: {
    name: string
    args: string
    timestamp: number
  }[]
}

function getToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem("auth_token")
}

export async function apiRequest<T>(path: string, opts: ApiOptions = {}): Promise<T> {
  const token = opts.token !== undefined ? opts.token : getToken()

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...opts.headers,
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }

  const url =
    path.startsWith("http://") || path.startsWith("https://")
      ? path
      : `${API_BASE}${path}`

  const res = await fetch(url, {
    method: opts.method || "GET",
    headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: res.statusText } }))
    throw new Error(err.error?.message || err.detail || "Request failed")
  }

  return res.json()
}

/**
 * Fetches the message history for a given session from GET /chats?session_id=<id>.
 * The backend returns an array of message objects from the agent's PostgreSQL store.
 */
export async function fetchChatHistory(
  sessionId: string,
  token: string | null,
): Promise<ChatMessage[]> {
  const headers: Record<string, string> = {}
  if (token) headers["Authorization"] = `Bearer ${token}`

  const res = await fetch(
    `${API_BASE}/chats?session_id=${encodeURIComponent(sessionId)}`,
    { headers },
  )

  if (!res.ok) {
    return []
  }

  const raw = await res.json()

  // The agno library returns message objects with a `role` and `content` field.
  // We normalise to our ChatMessage shape, skipping tool/system messages.
  if (!Array.isArray(raw)) return []

  const merged: ChatMessage[] = []
  for (const m of raw) {
    if (m.role !== "user" && m.role !== "assistant") {
      continue
    }

    const rawToolCalls = (m.tool_calls || []) as {
      function?: { name?: string; arguments?: string }
    }[]
    const toolCalls = rawToolCalls.map((tc) => ({
      name: tc.function?.name || "",
      args: tc.function?.arguments || "",
      timestamp: m.created_at ? (m.created_at as number) * 1000 : Date.now(),
    }))

    let content = ""
    if (m.content !== undefined && m.content !== null) {
      content = typeof m.content === "string" ? m.content : JSON.stringify(m.content)
    }

    if (m.role === "user") {
      merged.push({
        role: "user",
        content,
        ...(m.source === "voice" ? { source: "voice" as const } : {}),
        toolCalls: [],
      })
    } else if (m.role === "assistant") {
      const last = merged[merged.length - 1]
      const source = m.source === "voice" ? "voice" : undefined
      if (last && last.role === "assistant" && last.source === source) {
        if (content) {
          last.content = last.content ? last.content + "\n" + content : content
        }
        if (toolCalls.length > 0) {
          last.toolCalls = [...(last.toolCalls || []), ...toolCalls]
        }
      } else {
        merged.push({
          role: "assistant",
          content,
          ...(source ? { source } : {}),
          toolCalls,
        })
      }
    }
  }

  return merged
}

export function createSSEConnection(
  prompt: string,
  sessionId: string | null,
  token: string | null,
  onToolCall: (name: string, args: string) => void,
  onContent: (text: string) => void,
  onDone: () => void,
  onError: (error: string) => void,
): AbortController {
  const controller = new AbortController()

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  }
  if (token) headers["Authorization"] = `Bearer ${token}`

  fetch(`${API_BASE}/ask/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify({ prompt, session_id: sessionId }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        onError(`HTTP ${response.status}`)
        return
      }

      const reader = response.body?.getReader()
      if (!reader) {
        onError("No response body")
        return
      }

      const decoder = new TextDecoder()
      let buffer = ""
      let currentEvent = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = lines.pop() || ""

        for (const line of lines) {
          const trimmed = line.trim()
          if (trimmed.startsWith("event: ")) {
            currentEvent = trimmed.slice(7).trim()
          } else if (trimmed.startsWith("data: ")) {
            const data = trimmed.slice(6)
            if (data === "[DONE]") {
              onDone()
              return
            }

            if (currentEvent === "status" || currentEvent === "close") {
              continue
            }

            const toolMatch = data.match(/^Tool Call: (\w+)\((.*)\)$/)
            if (toolMatch) {
              onToolCall(toolMatch[1], toolMatch[2])
            } else {
              let parsedData = data
              if (data.startsWith('"') && data.endsWith('"')) {
                try {
                  parsedData = JSON.parse(data)
                } catch {
                  // fallback if parsing fails
                }
              }
              onContent(parsedData)
            }
          } else if (trimmed === "") {
            currentEvent = ""
          }
        }
      }
      onDone()
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(err.message)
      }
    })

  return controller
}

export async function retryChatMessage(
  sessionId: string,
  token: string | null,
): Promise<{ prompt: string }> {
  return apiRequest<{ prompt: string }>("/chats/retry", {
    method: "POST",
    body: { session_id: sessionId },
    token,
  })
}

export interface VoiceToken {
  server_url: string
  participant_token: string
  room_name: string
}

/**
 * Mints a short-lived LiveKit token. The backend also dispatches the voice
 * agent into the new room with this user's identity.
 */
export async function fetchVoiceToken(token: string | null): Promise<VoiceToken> {
  return apiRequest<VoiceToken>("/voice/token", {
    method: "POST",
    token,
  })
}

export async function saveVoiceTranscript(
  sessionId: string,
  message: { id: string; role: "user" | "assistant"; content: string },
  token: string | null,
): Promise<void> {
  await apiRequest("/voice/transcripts", {
    method: "POST",
    body: {
      session_id: sessionId,
      message_id: message.id,
      role: message.role,
      content: message.content,
    },
    token,
  })
}

export interface DocInfo {
  filename: string
  size_bytes: number
  uploaded_at: string
}

export async function listDocuments(token: string | null): Promise<DocInfo[]> {
  const res = await apiRequest<{ docs: DocInfo[] }>(docsApiUrl("/docs"), {
    method: "GET",
    token,
  })
  return res.docs || []
}

export async function uploadDocument(
  file: File,
  token: string | null,
): Promise<{ filename: string; message: string }> {
  const formData = new FormData()
  formData.append("file", file)

  const headers: Record<string, string> = {}
  if (token) headers["Authorization"] = `Bearer ${token}`

  const res = await fetch(docsApiUrl("/docs/upload"), {
    method: "POST",
    headers,
    body: formData,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: res.statusText } }))
    throw new Error(err.error?.message || err.detail || "Upload failed")
  }

  return res.json()
}

export async function deleteDocument(filename: string, token: string | null): Promise<void> {
  await apiRequest<void>(docsApiUrl(`/docs/${encodeURIComponent(filename)}`), {
    method: "DELETE",
    token,
  })
}
