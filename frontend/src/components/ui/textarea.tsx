import * as React from "react"

import { cn } from "@/lib/utils"

function Textarea({
  className,
  ...props
}: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "flex min-h-[60px] w-full rounded-lg border border-[#E5E7EB] bg-white px-3 py-2.5 text-sm text-[#1A1A2E] transition-colors placeholder:text-[#9CA3AF] focus-visible:border-[#2D5AE0] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2D5AE0]/15 disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
}

export { Textarea }
