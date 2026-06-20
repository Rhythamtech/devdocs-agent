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
      <div className="overflow-hidden rounded-lg border border-[#E5E7EB] bg-white transition-colors hover:border-[#D1D5DB]">
        <CollapsibleTrigger
          render={<Button
            variant="ghost"
            size="sm"
            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-[#6B7280] hover:text-[#374151] focus-visible:ring-2 focus-visible:ring-[#2D5AE0]/20"
          >
            <motion.div
              animate={{ rotate: open ? 90 : 0 }}
              transition={{ duration: prefersReduced ? 0 : 0.15 }}
            >
              <ChevronDown className="size-3.5" />
            </motion.div>
            <Code className="size-3.5 text-[#2D5AE0]" />
            <span className="font-medium text-[#374151]">{name}</span>
            <Badge
              variant="secondary"
              className="ml-auto bg-[#EEF2FF] text-[10px] text-[#2D5AE0] border-0"
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
                <div className="space-y-3 border-t border-[#E5E7EB] px-3 pb-3 pt-2">
                  <div className="space-y-1">
                    <p className="text-xs font-medium text-[#9CA3AF]">Arguments</p>
                    <pre className="overflow-x-auto rounded-lg bg-[#F9FAFB] border border-[#E5E7EB] p-3 font-mono text-xs leading-relaxed text-[#6B7280]">
                      {formatArgs(args)}
                    </pre>
                  </div>
                  {result && (
                    <div className="space-y-1">
                      <p className="text-xs font-medium text-[#9CA3AF]">Result</p>
                      <pre className="overflow-x-auto rounded-lg bg-[#F9FAFB] border border-[#E5E7EB] p-3 font-mono text-xs leading-relaxed text-[#6B7280]">
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
