"use client"

import { useState } from "react"
import { motion, AnimatePresence, useReducedMotion } from "motion/react"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ChevronDown, Code } from "lucide-react"

interface ToolCallCardProps {
  name: string
  args: string
  result?: string
}

export function ToolCallCard({ name, args, result }: ToolCallCardProps) {
  const [open, setOpen] = useState(false)
  const prefersReduced = useReducedMotion()

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <div className="overflow-hidden rounded-lg border border-border bg-card transition-colors hover:border-border/80">
        <CollapsibleTrigger
          render={<Button
            variant="ghost"
            size="sm"
            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:text-card-foreground focus-visible:ring-2 focus-visible:ring-primary/20"
          >
            <motion.div
              animate={{ rotate: open ? 90 : 0 }}
              transition={{ duration: prefersReduced ? 0 : 0.15 }}
            >
              <ChevronDown className="size-3.5" />
            </motion.div>
            <Code className="size-3.5 text-primary" />
            <span className="font-medium text-card-foreground">{name}</span>
            <Badge
              variant="secondary"
              className="ml-auto bg-primary/10 text-[10px] text-primary border-0"
            >
              tool
            </Badge>
          </Button>}
        />
        <CollapsibleContent>
          <AnimatePresence initial={false}>
            {open && (
              <motion.div
                initial={prefersReduced ? false : { height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                className="overflow-hidden"
              >
                <div className="space-y-3 border-t border-border px-3 pb-3 pt-2">
                  <div className="space-y-1">
                    <p className="text-xs font-medium text-muted-foreground/70">Arguments</p>
                    <pre className="overflow-x-auto rounded-lg bg-muted border border-border p-3 font-mono text-xs leading-relaxed text-muted-foreground">
                      {formatArgs(args)}
                    </pre>
                  </div>
                  {result && (
                    <div className="space-y-1">
                      <p className="text-xs font-medium text-muted-foreground/70">Result</p>
                      <pre className="overflow-x-auto rounded-lg bg-muted border border-border p-3 font-mono text-xs leading-relaxed text-muted-foreground">
                        {result}
                      </pre>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </CollapsibleContent>
      </div>
    </Collapsible>
  )
}

function formatArgs(args: string): string {
  try {
    const parsed = JSON.parse(args)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return args
  }
}
