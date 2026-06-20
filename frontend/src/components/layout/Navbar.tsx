"use client"

import Link from "next/link"
import { useAuth } from "@/contexts/AuthContext"
import { Button } from "@/components/ui/button"

export function Navbar() {
  const { isAuthenticated, user, logout } = useAuth()

  return (
    <nav className="sticky top-0 z-50 border-b border-[#E5E7EB] bg-[#FAFAF8]/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 text-sm font-semibold tracking-tight text-[#1A1A2E] transition-colors hover:text-[#2D5AE0]">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="18" height="18" rx="4" fill="#2D5AE0" fillOpacity="0.1" />
            <path d="M5 13V5L9 9L13 5V13" stroke="#2D5AE0" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          DevDocs
        </Link>

        <div className="flex items-center gap-1">
          {isAuthenticated ? (
            <>
              <Link href="/chat">
                <Button variant="ghost" size="sm">Chat</Button>
              </Link>
              <Link href="/profile">
                <Button variant="ghost" size="sm">
                  {user?.username || "Profile"}
                </Button>
              </Link>
              <Button variant="ghost" size="sm" onClick={logout}>
                Logout
              </Button>
            </>
          ) : (
            <>
              <Link href="/login">
                <Button variant="ghost" size="sm">Sign in</Button>
              </Link>
              <Link href="/signup">
                <Button variant="primary" size="sm">Get Started</Button>
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}
