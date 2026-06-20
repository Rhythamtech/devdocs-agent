"use client"

import { ProtectedRoute } from "@/components/layout/ProtectedRoute"
import { useAuth } from "@/contexts/AuthContext"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { User, Mail, LogOut } from "lucide-react"

function ProfilePage() {
  const { user, logout } = useAuth()

  return (
    <ProtectedRoute>
      <div className="flex flex-1 items-start justify-center p-8">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto mb-2 flex size-14 items-center justify-center rounded-full bg-primary/10">
              <User className="size-6 text-primary" />
            </div>
            <CardTitle>{user?.username}</CardTitle>
            <CardDescription>{user?.email}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Separator />
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-3 text-muted-foreground">
                <User className="size-4 shrink-0" />
                <span className="w-20 shrink-0">Username</span>
                <span className="text-card-foreground">{user?.username}</span>
              </div>
              <div className="flex items-center gap-3 text-muted-foreground">
                <Mail className="size-4 shrink-0" />
                <span className="w-20 shrink-0">Email</span>
                <span className="text-card-foreground">{user?.email}</span>
              </div>
            </div>
            <Separator />
            <Button variant="destructive" className="w-full gap-2" onClick={logout}>
              <LogOut className="size-4" />
              Sign Out
            </Button>
          </CardContent>
        </Card>
      </div>
    </ProtectedRoute>
  )
}

export default function Page() {
  return <ProfilePage />
}
