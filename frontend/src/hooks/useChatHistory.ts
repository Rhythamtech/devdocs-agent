"use client"

import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"
import { deleteAllSessions, fetchSessions } from "@/lib/api"

export interface LocalChatSession {
  session_id: string
  title: string
  created_at: string
}

const STORAGE_KEY = "chat_sessions"

function loadFromStorage(): LocalChatSession[] {
  if (typeof window === "undefined") return []
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as LocalChatSession[]) : []
  } catch {
    return []
  }
}

function saveToStorage(sessions: LocalChatSession[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
}

/** Backend timestamps are epoch seconds; locally created ones are ISO strings. */
function toEpoch(value: string): number {
  if (!value) return 0
  const numeric = Number(value)
  if (Number.isFinite(numeric)) return numeric
  const parsed = Date.parse(value)
  return Number.isNaN(parsed) ? 0 : parsed / 1000
}

/**
 * Merge server sessions with anything still only in localStorage. The server
 * is the source of truth, but a session created moments ago may not have been
 * persisted yet, so keep local-only entries too.
 */
function mergeSessions(
  local: LocalChatSession[],
  remote: LocalChatSession[],
): LocalChatSession[] {
  const byId = new Map<string, LocalChatSession>()
  for (const session of local) {
    byId.set(session.session_id, session)
  }
  for (const session of remote) {
    const existing = byId.get(session.session_id)
    const remoteTitle =
      session.title && session.title !== session.session_id ? session.title : ""
    byId.set(session.session_id, {
      session_id: session.session_id,
      title: remoteTitle || existing?.title || session.title || "Untitled",
      created_at: session.created_at || existing?.created_at || "",
    })
  }
  return [...byId.values()].sort((a, b) => toEpoch(b.created_at) - toEpoch(a.created_at))
}

export function useChatHistory(token: string | null = null) {
  const [sessions, setSessions] = useState<LocalChatSession[]>([])
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    const local = loadFromStorage()
    setSessions(local)

    if (!token) return

    try {
      const remote = await fetchSessions(token)
      const merged = mergeSessions(local, remote)
      saveToStorage(merged)
      setSessions(merged)
    } catch {
      // Backend unreachable — keep showing the local list.
    }
  }, [token])

  useEffect(() => {
    let cancelled = false
    void refresh().finally(() => {
      if (!cancelled) setLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [refresh])

  const addSession = useCallback((sessionId: string, firstMessage: string) => {
    setSessions((prev) => {
      // Avoid duplicates
      if (prev.some((s) => s.session_id === sessionId)) return prev
      const title =
        firstMessage.length > 50
          ? firstMessage.slice(0, 50).trimEnd() + "…"
          : firstMessage
      const next: LocalChatSession[] = [
        { session_id: sessionId, title, created_at: new Date().toISOString() },
        ...prev,
      ]
      saveToStorage(next)
      return next
    })
  }, [])

  const clearAll = useCallback(async () => {
    localStorage.removeItem(STORAGE_KEY)
    setSessions([])

    if (!token) return
    try {
      await deleteAllSessions(token)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Could not clear server history.",
      )
    }
  }, [token])

  return { sessions, loading, addSession, clearAll, refresh }
}
