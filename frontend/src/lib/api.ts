const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

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

// Shape returned by GET /chats?session_id=<id>
export interface ChatMessage {
  role: "user" | "assistant"
  content: string
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

  const res = await fetch(`${API_BASE}${path}`, {
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
 * The backend returns an array of message objects from the agent's MongoDB store.
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

  return raw
    .filter((m: Record<string, unknown>) => m.role === "user" || m.role === "assistant")
    .map((m: Record<string, unknown>) => ({
      role: m.role as "user" | "assistant",
      content: typeof m.content === "string" ? m.content : JSON.stringify(m.content ?? ""),
    }))
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

export interface DocInfo {
  filename: string
  size_bytes: number
  uploaded_at: string
}

export async function listDocuments(token: string | null): Promise<DocInfo[]> {
  const res = await apiRequest<{ docs: DocInfo[] }>("/docs", {
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

  const res = await fetch(`${API_BASE}/docs/upload`, {
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
  await apiRequest<void>(`/docs/${encodeURIComponent(filename)}`, {
    method: "DELETE",
    token,
  })
}

