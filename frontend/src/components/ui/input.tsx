import * as React from "react"

import { cn } from "@/lib/utils"

function Input({
  className,
  type = "text",
  ...props
}: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "flex h-10 w-full rounded-lg border border-[#E5E7EB] bg-white px-3 py-2 text-sm text-[#1A1A2E] transition-colors placeholder:text-[#9CA3AF] focus-visible:border-[#2D5AE0] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2D5AE0]/15 disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
}

export { Input }
