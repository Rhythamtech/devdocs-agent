"use client"

import { useCallback, useEffect, useState } from "react"

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

export function useChatHistory() {
  const [sessions, setSessions] = useState<LocalChatSession[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setSessions(loadFromStorage())
    setLoading(false)
  }, [])

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

  const clearAll = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setSessions([])
  }, [])

  const refresh = useCallback(() => {
    setSessions(loadFromStorage())
  }, [])

  return { sessions, loading, addSession, clearAll, refresh }
}
