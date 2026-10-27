"use client"

import { AnimatePresence, motion, useReducedMotion } from "motion/react"
import { Loader2, Mic, MicOff, PhoneOff, Volume2, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { VoiceStatus } from "@/hooks/useVoiceSession"

const STATUS_LABEL: Record<VoiceStatus, string> = {
  idle: "Voice ready",
  connecting: "Connecting…",
  listening: "Listening",
  thinking: "Searching your docs…",
  speaking: "DevDocs is speaking…",
  error: "Voice unavailable",
}

const STATUS_HINT: Record<VoiceStatus, string> = {
  idle: "Tap the mic to talk to your documentation.",
  connecting: "Setting up a private room.",
  listening: "Ask a question, then pause when you're done.",
  thinking: "Looking through your uploaded files.",
  speaking: "You can interrupt at any time.",
  error: "Check your connection and try again.",
}

function Waveform({ animated }: { animated: boolean }) {
  const prefersReduced = useReducedMotion()

  return (
    <div className="flex h-4 items-center gap-[3px]" aria-hidden>
      {[0, 1, 2, 3].map((i) => (
        <motion.span
          key={i}
          className="w-[3px] rounded-full bg-primary"
          initial={{ height: 6 }}
          animate={
            animated && !prefersReduced
              ? { height: [5, 14, 8, 16, 6] }
              : { height: 6 }
          }
          transition={{
            duration: 1.1,
            repeat: animated && !prefersReduced ? Infinity : 0,
            delay: i * 0.12,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  )
}

interface VoiceMicButtonProps {
  active: boolean
  disabled?: boolean
  onClick: () => void
}

/** Mic toggle that sits in the composer next to the send button. */
export function VoiceMicButton({ active, disabled, onClick }: VoiceMicButtonProps) {
  return (
    <Button
      type="button"
      variant={active ? "primary" : "ghost"}
      size="icon"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={active}
      aria-label={active ? "End voice mode" : "Start voice mode"}
      title={active ? "End voice mode" : "Talk to DevDocs"}
      className={cn(
        "mb-0.5 rounded-xl",
        active && "shadow-[0_0_0_4px_rgba(251,146,60,0.15)]",
      )}
    >
      <Mic className="size-4" />
    </Button>
  )
}

interface VoiceStatusStripProps {
  active: boolean
  status: VoiceStatus
  error: string | null
  audioBlocked?: boolean
  onStop: () => void
  onDismiss: () => void
  onResumeAudio?: () => void
}

/** Live agent-state indicator shown above the composer while voice is on. */
export function VoiceStatusStrip({
  active,
  status,
  error,
  audioBlocked = false,
  onStop,
  onDismiss,
  onResumeAudio,
}: VoiceStatusStripProps) {
  const isError = Boolean(error) && !active
  const visible = active || isError
  const displayStatus: VoiceStatus = isError ? "error" : status
  const busy = displayStatus === "connecting" || displayStatus === "thinking"
  const speaking = displayStatus === "speaking"
  const listening = displayStatus === "listening"

  return (
    <AnimatePresence initial={false}>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.18 }}
          role={isError ? "alert" : "status"}
          aria-live="polite"
          className={cn(
            "flex items-center gap-3 rounded-xl border px-3.5 py-2.5",
            isError
              ? "border-destructive/30 bg-destructive/5"
              : "border-border bg-card",
          )}
        >
          <span
            className={cn(
              "flex size-8 shrink-0 items-center justify-center rounded-lg",
              isError ? "bg-destructive/10" : "bg-primary/10",
            )}
          >
            {isError ? (
              <MicOff className="size-4 text-destructive" />
            ) : busy ? (
              <Loader2 className="size-4 animate-spin text-primary" />
            ) : (
              <Waveform animated={speaking || listening} />
            )}
          </span>

          <div className="min-w-0 flex-1">
            <p
              className={cn(
                "text-xs font-medium",
                isError ? "text-destructive" : "text-foreground",
              )}
            >
              {STATUS_LABEL[displayStatus]}
            </p>
            <p
              className="truncate text-[11px] text-muted-foreground"
              title={isError ? (error ?? undefined) : undefined}
            >
              {isError
                ? error
                : audioBlocked
                  ? "Enable audio to hear DevDocs speak."
                  : STATUS_HINT[displayStatus]}
            </p>
          </div>

          {active && audioBlocked && onResumeAudio && (
            <Button
              type="button"
              variant="outline"
              size="xs"
              onClick={onResumeAudio}
              className="gap-1.5"
            >
              <Volume2 className="size-3.5" />
              Enable audio
            </Button>
          )}

          {active ? (
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              onClick={onStop}
              aria-label="End voice mode"
              title="End voice mode"
            >
              <PhoneOff className="size-4" />
            </Button>
          ) : (
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              onClick={onDismiss}
              aria-label="Dismiss voice error"
              title="Dismiss"
            >
              <X className="size-4" />
            </Button>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
