"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "motion/react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Plus, Trash2, MessageSquare } from "lucide-react"
import { toast } from "sonner"
import type { LocalChatSession } from "@/hooks/useChatHistory"

interface ChatSidebarProps {
  sessions: LocalChatSession[]
  currentSessionId: string | null
  onSelect: (id: string) => void
  onNew: () => void
  onClearAll: () => void
}

export function ChatSidebar({
  sessions,
  currentSessionId,
  onSelect,
  onNew,
  onClearAll,
}: ChatSidebarProps) {
  const [confirmClear, setConfirmClear] = useState(false)

  const handleClearAll = () => {
    if (!confirmClear) {
      setConfirmClear(true)
      setTimeout(() => setConfirmClear(false), 3000)
      return
    }
    onClearAll()
    setConfirmClear(false)
    toast.success("All conversations cleared")
  }

  return (
    <div className="flex h-full flex-col border-r border-border bg-muted">
      <div className="p-3">
        <Button
          onClick={onNew}
          className="w-full gap-2"
          size="sm"
        >
          <Plus className="size-4" />
          New Chat
        </Button>
      </div>

      <Separator />

      <ScrollArea className="flex-1">
        <div className="space-y-0.5 p-2">
          {sessions.length === 0 ? (
            <p className="px-3 py-8 text-center text-xs text-muted-foreground/70">
              No conversations yet
            </p>
          ) : (
            <AnimatePresence initial={false}>
              {sessions.map((session) => {
                const isActive = currentSessionId === session.session_id
                return (
                  <motion.button
                    key={session.session_id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.15 }}
                    onClick={() => onSelect(session.session_id)}
                    className={`
                      relative w-full cursor-pointer rounded-lg px-3 py-2.5 text-left text-sm transition-colors duration-150
                      focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 focus-visible:border-primary
                      ${isActive
                        ? "bg-primary/10 text-foreground font-medium"
                        : "text-muted-foreground hover:bg-card hover:text-card-foreground"
                      }
                    `}
                  >
                    {isActive && (
                      <motion.div
                        layoutId="activeSession"
                        className="absolute inset-y-0 left-0 w-[2px] rounded-full bg-primary"
                        transition={{ type: "spring", stiffness: 300, damping: 30 }}
                      />
                    )}
                    <span className="flex items-center gap-2.5">
                      <MessageSquare className="size-4 shrink-0" />
                      <span className="truncate">{session.title || "Untitled"}</span>
                    </span>
                  </motion.button>
                )
              })}
            </AnimatePresence>
          )}
        </div>
      </ScrollArea>

      <Separator />

      <div className="p-2">
        <Button
          variant="ghost"
          size="sm"
          className={`w-full gap-2 text-sm transition-colors ${
            confirmClear
              ? "text-destructive bg-destructive/10 hover:bg-destructive/20"
              : "text-muted-foreground/70 hover:text-destructive"
          }`}
          onClick={handleClearAll}
        >
          <Trash2 className="size-3.5" />
          {confirmClear ? "Confirm clear" : "Clear all"}
        </Button>
      </div>
    </div>
  )
}
