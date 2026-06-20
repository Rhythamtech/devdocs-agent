"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { motion, AnimatePresence, useReducedMotion } from "motion/react"
import { ProtectedRoute } from "@/components/layout/ProtectedRoute"
import { ChatSidebar } from "@/components/chat/ChatSidebar"
import { ToolCallCard } from "@/components/chat/ToolCallCard"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Sheet, SheetContent } from "@/components/ui/sheet"
import { useAuth } from "@/contexts/AuthContext"
import { createSSEConnection, fetchChatHistory, retryChatMessage } from "@/lib/api"
import { Send, Bot, Menu, ArrowRight, RotateCcw, ArrowDown } from "lucide-react"
import { useChatHistory } from "@/hooks/useChatHistory"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

interface ToolCall {
  name: string
  args: string
  timestamp: number
}

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  toolCalls: ToolCall[]
}

function generateId() {
  return Math.random().toString(36).substring(2, 11)
}

/** Generate a UUID v4 for session IDs */
function generateSessionId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  // Fallback for environments without crypto.randomUUID
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === "x" ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

function ChatPage() {
  const { token } = useAuth()
  const { sessions, addSession, clearAll, refresh: refreshSessions } = useChatHistory()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [streaming, setStreaming] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const contentRef = useRef<HTMLDivElement>(null)
  const scrollViewportRef = useRef<HTMLDivElement | null>(null)
  const isAtBottomRef = useRef(true)
  const [showScrollDown, setShowScrollDown] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const prefersReduced = useReducedMotion()

  // Set up viewport ref and scroll event listener on mount
  useEffect(() => {
    const viewport = contentRef.current?.closest('[data-slot="scroll-area"]')
      ?.querySelector('[data-slot="scroll-area-viewport"]') as HTMLDivElement | null
    if (!viewport) return
    scrollViewportRef.current = viewport

    const handleScroll = () => {
      const { scrollHeight, scrollTop, clientHeight } = viewport
      const atBottom = scrollHeight - scrollTop - clientHeight < 100
      isAtBottomRef.current = atBottom
      setShowScrollDown(!atBottom)
    }

    viewport.addEventListener("scroll", handleScroll, { passive: true })
    // Initial check
    handleScroll()
    return () => viewport.removeEventListener("scroll", handleScroll)
  }, [])

  // Auto-scroll only when user is at bottom
  useEffect(() => {
    if (isAtBottomRef.current && scrollViewportRef.current) {
      const viewport = scrollViewportRef.current
      requestAnimationFrame(() => {
        viewport.scrollTop = viewport.scrollHeight
      })
    }
  }, [messages])

  const scrollToBottom = useCallback(() => {
    if (scrollViewportRef.current) {
      scrollViewportRef.current.scrollTo({
        top: scrollViewportRef.current.scrollHeight,
        behavior: prefersReduced ? "auto" : "smooth",
      })
      isAtBottomRef.current = true
      setShowScrollDown(false)
    }
  }, [prefersReduced])

  /** Load history from the backend when a session is selected from the sidebar */
  const loadSession = useCallback(
    async (sessionId: string) => {
      setCurrentSessionId(sessionId)
      setMessages([])
      setLoadingHistory(true)
      setSidebarOpen(false)

      try {
        const history = await fetchChatHistory(sessionId, token)
        const mapped: Message[] = history.map((m) => ({
          id: generateId(),
          role: m.role,
          content: m.content,
          toolCalls: [],
        }))
        setMessages(mapped)
      } catch {
        // History unavailable — start fresh in this session
        setMessages([])
      } finally {
        setLoadingHistory(false)
      }
    },
    [token],
  )

  const sendMessage = useCallback(async () => {
    const prompt = input.trim()
    if (!prompt || streaming) return

    setInput("")
    setStreaming(true)

    // Assign a session ID for this conversation if we don't have one yet
    let sessionId = currentSessionId
    if (!sessionId) {
      sessionId = generateSessionId()
      setCurrentSessionId(sessionId)
      // Register in sidebar immediately with the first user message as title
      addSession(sessionId, prompt)
    }

    const userMsg: Message = {
      id: generateId(),
      role: "user",
      content: prompt,
      toolCalls: [],
    }

    const assistantMsg: Message = {
      id: generateId(),
      role: "assistant",
      content: "",
      toolCalls: [],
    }

    setMessages((prev) => [...prev, userMsg, assistantMsg])

    const controller = createSSEConnection(
      prompt,
      sessionId,
      token,
      (name, args) => {
        setMessages((prev) => {
          if (prev.length === 0) return prev
          const updated = [...prev]
          const lastIdx = updated.length - 1
          const last = updated[lastIdx]
          if (last?.role === "assistant") {
            updated[lastIdx] = {
              ...last,
              toolCalls: [...last.toolCalls, { name, args, timestamp: Date.now() }],
            }
          }
          return updated
        })
      },
      (text) => {
        setMessages((prev) => {
          if (prev.length === 0) return prev
          const updated = [...prev]
          const lastIdx = updated.length - 1
          const last = updated[lastIdx]
          if (last?.role === "assistant") {
            updated[lastIdx] = {
              ...last,
              content: last.content + text,
            }
          }
          return updated
        })
      },
      () => {
        setStreaming(false)
        refreshSessions()
      },
      (error) => {
        setMessages((prev) => {
          if (prev.length === 0) return prev
          const updated = [...prev]
          const lastIdx = updated.length - 1
          const last = updated[lastIdx]
          if (last?.role === "assistant") {
            updated[lastIdx] = {
              ...last,
              content: last.content + `\n\n*Error: ${error}*`,
            }
          }
          return updated
        })
        setStreaming(false)
      },
    )

    abortRef.current = controller
  }, [input, streaming, token, currentSessionId, addSession, refreshSessions])

  const handleRetry = useCallback(async () => {
    if (!currentSessionId || streaming) return

    setStreaming(true)

    try {
      const { prompt } = await retryChatMessage(currentSessionId, token)

      // Remove the last user message and assistant response from the UI list
      setMessages((prev) => prev.slice(0, -2))

      const userMsg: Message = {
        id: generateId(),
        role: "user",
        content: prompt,
        toolCalls: [],
      }

      const assistantMsg: Message = {
        id: generateId(),
        role: "assistant",
        content: "",
        toolCalls: [],
      }

      setMessages((prev) => [...prev, userMsg, assistantMsg])

      const controller = createSSEConnection(
        prompt,
        currentSessionId,
        token,
        (name, args) => {
          setMessages((prev) => {
            if (prev.length === 0) return prev
            const updated = [...prev]
            const lastIdx = updated.length - 1
            const last = updated[lastIdx]
            if (last?.role === "assistant") {
              updated[lastIdx] = {
                ...last,
                toolCalls: [...last.toolCalls, { name, args, timestamp: Date.now() }],
              }
            }
            return updated
          })
        },
        (text) => {
          setMessages((prev) => {
            if (prev.length === 0) return prev
            const updated = [...prev]
            const lastIdx = updated.length - 1
            const last = updated[lastIdx]
            if (last?.role === "assistant") {
              updated[lastIdx] = {
                ...last,
                content: last.content + text,
              }
            }
            return updated
          })
        },
        () => {
          setStreaming(false)
          refreshSessions()
        },
        (error) => {
          setMessages((prev) => {
            if (prev.length === 0) return prev
            const updated = [...prev]
            const lastIdx = updated.length - 1
            const last = updated[lastIdx]
            if (last?.role === "assistant") {
              updated[lastIdx] = {
                ...last,
                content: last.content + `\n\n*Error: ${error}*`,
              }
            }
            return updated
          })
          setStreaming(false)
        },
      )

      abortRef.current = controller
    } catch (err: any) {
      setMessages((prev) => {
        if (prev.length === 0) return prev
        const updated = [...prev]
        const lastIdx = updated.length - 1
        const last = updated[lastIdx]
        if (last?.role === "assistant") {
          updated[lastIdx] = {
            ...last,
            content: last.content + `\n\n*Error during retry: ${err.message || err}*`,
          }
        }
        return updated
      })
      setStreaming(false)
    }
  }, [currentSessionId, streaming, token, refreshSessions])


  const handleNewChat = useCallback(() => {
    // Abort any in-progress stream
    abortRef.current?.abort()
    setMessages([])
    setCurrentSessionId(null)
    setInput("")
    setSidebarOpen(false)
    inputRef.current?.focus()
  }, [])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const motionProps = prefersReduced
    ? {}
    : { initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: -8 } }

  return (
    <ProtectedRoute>
      <div className="flex h-[calc(100dvh-3.5rem)] w-full overflow-hidden">
        <aside className="hidden w-72 shrink-0 md:block">
          <ChatSidebar
            sessions={sessions}
            currentSessionId={currentSessionId}
            onSelect={loadSession}
            onNew={handleNewChat}
            onClearAll={clearAll}
          />
        </aside>

        <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
          <Button
            variant="ghost"
            size="icon"
            className="fixed left-3 top-16 z-40 md:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="size-5" />
          </Button>
          <SheetContent side="left" className="w-72 p-0">
            <ChatSidebar
              sessions={sessions}
              currentSessionId={currentSessionId}
              onSelect={(id) => {
                loadSession(id)
              }}
              onNew={handleNewChat}
              onClearAll={clearAll}
            />
          </SheetContent>
        </Sheet>

        <div className="relative flex min-h-0 flex-1 flex-col">
          <ScrollArea className="relative z-10 flex-1">
            <div ref={contentRef} className="mx-auto max-w-3xl space-y-6 px-6 py-10 md:px-8">
              <AnimatePresence mode="popLayout">
                {messages.length === 0 && !loadingHistory && (
                  <motion.div
                    key="empty"
                    {...motionProps}
                    transition={{ duration: 0.3 }}
                    className="flex flex-col items-center justify-center py-28 text-center"
                  >
                    <div className="mb-5 flex size-12 items-center justify-center rounded-xl bg-primary/10">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M7 17L17 7M17 7H7M17 7V17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-primary" />
                      </svg>
                    </div>
                    <h2 className="text-lg font-semibold text-foreground">
                      What do you need to know?
                    </h2>
                    <p className="mt-1.5 max-w-sm text-sm text-muted-foreground">
                      Ask anything about your documentation. Every answer includes its source.
                    </p>
                    <div className="mt-6">
                      <Button variant="outline" size="sm" className="gap-2" onClick={handleNewChat}>
                        Start a conversation
                        <ArrowRight className="size-3.5" />
                      </Button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {loadingHistory && (
                <div className="flex items-center justify-center py-16 text-sm text-muted-foreground/70">
                  <div className="flex gap-1 mr-2">
                    <span className="size-1.5 rounded-full bg-primary animate-pulse" style={{ animationDelay: "0ms" }} />
                    <span className="size-1.5 rounded-full bg-primary animate-pulse" style={{ animationDelay: "200ms" }} />
                    <span className="size-1.5 rounded-full bg-primary animate-pulse" style={{ animationDelay: "400ms" }} />
                  </div>
                  Loading conversation…
                </div>
              )}

              <AnimatePresence initial={false}>
                {messages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    layout
                    initial={prefersReduced ? false : { opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2 }}
                    className="space-y-3"
                  >
                    {msg.role === "user" ? (
                      <div className="flex justify-end">
                        <div className="max-w-[80%]">
                          <div className="rounded-2xl rounded-br-md bg-primary px-4 py-3 text-[15px] leading-relaxed text-primary-foreground">
                            {msg.content}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                          <Bot className="size-4 text-primary" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="mb-1 text-xs font-medium text-muted-foreground/70">
                            DevDocs
                          </p>
                          {msg.content ? (
                            <div className="text-[15px] leading-relaxed text-card-foreground prose-p:my-2 prose-pre:my-3 prose-headings:text-foreground prose-a:text-primary prose-strong:text-foreground prose-code:rounded-md prose-code:bg-secondary prose-code:px-1.5 prose-code:py-0.5 prose-code:text-primary prose-code:before:content-none prose-code:after:content-none prose-pre:border prose-pre:border-border prose-pre:bg-muted prose-pre:p-4 prose-ol:my-2 prose-ul:my-2 prose-li:my-1">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {msg.content}
                              </ReactMarkdown>
                            </div>
                          ) : (
                            msg.role === "assistant" && streaming && (
                              <div className="flex items-center gap-2 text-muted-foreground/70">
                                <div className="flex gap-1">
                                  <span className="size-1.5 rounded-full bg-primary animate-pulse" style={{ animationDelay: "0ms" }} />
                                  <span className="size-1.5 rounded-full bg-primary animate-pulse" style={{ animationDelay: "200ms" }} />
                                  <span className="size-1.5 rounded-full bg-primary animate-pulse" style={{ animationDelay: "400ms" }} />
                                </div>
                                <span className="text-sm">
                                  Thinking...
                                </span>
                              </div>
                            )
                          )}
                          {msg.role === "assistant" && msg.id === messages[messages.length - 1]?.id && !streaming && (
                            <div className="mt-2 flex items-center gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={handleRetry}
                                className="h-7 gap-1 px-2 text-xs text-muted-foreground hover:text-primary hover:bg-primary/10 rounded-lg transition-colors"
                              >
                                <RotateCcw className="size-3.5" />
                                Rerun Response
                              </Button>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {msg.toolCalls.length > 0 && (
                      <div className="ml-11">
                        <div className="space-y-1.5">
                          {msg.toolCalls.map((tc, i) => (
                            <motion.div
                              key={`${tc.timestamp}-${i}`}
                              initial={prefersReduced ? false : { opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: "auto" }}
                              transition={{ duration: 0.15, delay: i * 0.03 }}
                            >
                              <ToolCallCard name={tc.name} args={tc.args} />
                            </motion.div>
                          ))}
                        </div>
                      </div>
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </ScrollArea>

          {/* Scroll to bottom FAB */}
          <AnimatePresence>
            {showScrollDown && (
              <motion.div
                initial={prefersReduced ? false : { opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={prefersReduced ? undefined : { opacity: 0, y: 8 }}
                transition={{ duration: 0.15 }}
                className="absolute bottom-28 left-1/2 z-20 -translate-x-1/2"
              >
                <Button
                  variant="default"
                  size="icon-sm"
                  className="rounded-full shadow-lg"
                  onClick={scrollToBottom}
                >
                  <ArrowDown className="size-4" />
                </Button>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="border-t border-border bg-background px-6 pb-4 pt-3">
            <div className="mx-auto flex max-w-3xl items-end gap-3">
              <Textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question..."
                className="min-h-11 resize-none rounded-xl border-border bg-card text-[15px] leading-relaxed text-foreground placeholder:text-muted-foreground focus-visible:border-primary focus-visible:ring-primary/15"
                rows={1}
                disabled={streaming}
              />
              <Button
                onClick={sendMessage}
                disabled={!input.trim() || streaming}
                variant="primary"
                size="icon"
                className="mb-0.5 rounded-xl"
              >
                <Send className="size-4" />
              </Button>
            </div>
            <p className="mt-2 text-center text-xs text-muted-foreground/70">
              Every answer includes source references from your documentation
            </p>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  )
}

export default function Page() {
  return <ChatPage />
}
