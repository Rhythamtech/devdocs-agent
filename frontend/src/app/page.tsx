"use client"

import Link from "next/link"
import { useAuth } from "@/contexts/AuthContext"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Search, BookOpen, MessageSquare, ArrowRight } from "lucide-react"

const features = [
  {
    icon: Search,
    title: "Semantic Search",
    description: "Natural language queries that understand intent, not just keywords.",
  },
  {
    icon: BookOpen,
    title: "Multi-Source Ingestion",
    description: "Connect wikis, READMEs, API docs — one knowledge graph, better answers.",
  },
  {
    icon: MessageSquare,
    title: "Conversational Memory",
    description: "Follow-ups that build on context. No re-explaining.",
  },
]

export default function HomePage() {
  const { isAuthenticated } = useAuth()

  return (
    <>
      <section className="flex flex-1 items-start px-6 lg:px-12">
        <div className="mx-auto grid w-full max-w-6xl grid-cols-1 items-center gap-12 py-16 md:py-24 lg:grid-cols-2 lg:gap-16">
          <div className="max-w-xl">
            <div className="mb-4 inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
              <span className="size-1.5 rounded-full bg-emerald-500" />
              NovaFlow
            </div>
            <h1 className="text-3xl font-bold leading-[1.15] tracking-tight text-foreground md:text-4xl lg:text-[42px]">
              Ask your documentation.
              <br />
              <span className="text-primary">Get source-backed answers.</span>
            </h1>
            <p className="mt-5 max-w-md text-base leading-relaxed text-muted-foreground">
              DevDocs connects your wikis, READMEs, and API docs into a single conversational interface. Every answer traces back to its source.
            </p>
            <div className="mt-8 flex items-center gap-3">
              {isAuthenticated ? (
                <Link href="/chat">
                  <Button variant="primary" size="lg" className="gap-2.5">
                    Open Chat
                    <ArrowRight className="size-4" />
                  </Button>
                </Link>
              ) : (
                <>
                  <Link href="/signup">
                    <Button variant="primary" size="lg" className="gap-2.5">
                      Get Started
                      <ArrowRight className="size-4" />
                    </Button>
                  </Link>
                  <Link href="/login">
                    <Button variant="ghost" size="lg">
                      Sign in
                    </Button>
                  </Link>
                </>
              )}
            </div>
          </div>

          <div className="relative">
            <div className="overflow-hidden rounded-xl border border-border bg-card shadow-lg shadow-black/5">
              <div className="flex items-center gap-2 border-b border-border bg-muted px-4 py-2.5">
                <div className="flex gap-1.5">
                  <span className="size-2.5 rounded-full bg-border" />
                  <span className="size-2.5 rounded-full bg-border" />
                  <span className="size-2.5 rounded-full bg-border" />
                </div>
                <span className="ml-2 text-xs font-medium text-muted-foreground">terminal</span>
              </div>
              <div className="p-5 font-mono text-[13px] leading-relaxed">
                <div className="flex gap-2">
                  <span className="text-emerald-500">$</span>
                  <span className="text-foreground">How does rate limiting work?</span>
                </div>
                <div className="mt-3 flex gap-2">
                  <span className="text-primary">&gt;</span>
                  <span className="text-muted-foreground">Rate limiting uses a sliding window algorithm...</span>
                </div>
                <div className="mt-1 pl-4 text-muted-foreground/70">
                  Source: api-docs/rate-limiting.md (line 12)
                </div>
                <div className="mt-3 flex gap-2">
                  <span className="text-primary">&gt;</span>
                  <span className="text-muted-foreground">The default limit is 100 requests per minute...</span>
                </div>
                <div className="mt-1 pl-4 text-muted-foreground/70">
                  Source: api-docs/rate-limiting.md (line 24)
                </div>
                <div className="mt-4 flex gap-2">
                  <span className="text-primary">&gt;</span>
                  <span className="inline-block size-2 bg-primary animate-pulse" />
                </div>
              </div>
            </div>
            <div className="absolute -bottom-3 -right-3 -z-10 size-full rounded-xl border border-border bg-secondary" />
          </div>
        </div>
      </section>

      <section className="border-t border-border bg-muted px-6 lg:px-12">
        <div className="mx-auto max-w-6xl py-16 md:py-20">
          <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
            {features.map((feature) => {
              const Icon = feature.icon
              return (
                <Card key={feature.title}>
                  <CardHeader>
                    <div className="mb-1 flex size-9 items-center justify-center rounded-lg bg-primary/10">
                      <Icon className="size-4.5 text-primary" />
                    </div>
                    <CardTitle>{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription>{feature.description}</CardDescription>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </div>
      </section>
    </>
  )
}
