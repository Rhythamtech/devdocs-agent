"use client"

import { TooltipProvider } from "@/components/ui/tooltip"
import { Toaster } from "@/components/ui/sonner"
import { AuthProvider } from "@/contexts/AuthContext"
import { Navbar } from "@/components/layout/Navbar"

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <TooltipProvider>
      <AuthProvider>
        <Navbar />
        <main className="flex flex-1 flex-col">{children}</main>
        <Toaster />
      </AuthProvider>
    </TooltipProvider>
  )
}
