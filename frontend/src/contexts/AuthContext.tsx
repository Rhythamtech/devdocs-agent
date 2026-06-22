"use client"

import { createContext, useCallback, useContext, useEffect, useState } from "react"
import { apiRequest, type UserProfile } from "@/lib/api"
import { useRouter } from "next/navigation"

interface AuthState {
  user: UserProfile | null
  token: string | null
  isLoading: boolean
  isAuthenticated: boolean
}

interface AuthContextType extends AuthState {
  login: (username: string, password: string) => Promise<void>
  signup: (username: string, email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    isLoading: true,
    isAuthenticated: false,
  })

  useEffect(() => {
    const token = localStorage.getItem("auth_token")
    if (token) {
      apiRequest<UserProfile>("/auth/me", { token })
        .then((user) => {
          setState({ user, token, isLoading: false, isAuthenticated: true })
        })
        .catch(() => {
          localStorage.removeItem("auth_token")
          setState({ user: null, token: null, isLoading: false, isAuthenticated: false })
        })
    } else {
      setState((s) => ({ ...s, isLoading: false }))
    }
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    const formData = new URLSearchParams()
    formData.append("username", username)
    formData.append("password", password)

    const isMock = process.env.NEXT_PUBLIC_MOCK_MODE === "true"

    let result: { access_token: string }
    if (isMock) {
      result = await apiRequest<{ access_token: string; token_type: string }>("/auth/login", {
        method: "POST",
        body: { username, password },
      })
    } else {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? ""}/auth/login`,
        {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: formData.toString(),
        },
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: { message: "Login failed" } }))
        throw new Error(err.error?.message || err.detail || "Login failed")
      }
      result = await res.json()
    }

    localStorage.setItem("auth_token", result.access_token)
    const user = await apiRequest<UserProfile>("/auth/me", { token: result.access_token })
    setState({ user, token: result.access_token, isLoading: false, isAuthenticated: true })
  }, [])

  const signup = useCallback(async (username: string, email: string, password: string) => {
    await apiRequest("/auth/signup", {
      method: "POST",
      body: { username, email, password },
    })
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem("auth_token")
    setState({ user: null, token: null, isLoading: false, isAuthenticated: false })
    router.push("/")
  }, [router])

  return (
    <AuthContext.Provider value={{ ...state, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
