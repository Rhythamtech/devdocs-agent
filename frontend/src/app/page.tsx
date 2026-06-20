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
            <div className="mb-4 inline-flex items-center gap-1.5 rounded-full border border-[#E5E7EB] bg-white px-2.5 py-0.5 text-xs font-medium text-[#6B7280]">
              <span className="size-1.5 rounded-full bg-[#059669]" />
              NovaFlow
            </div>
            <h1 className="text-3xl font-bold leading-[1.15] tracking-tight text-[#1A1A2E] md:text-4xl lg:text-[42px]">
              Ask your documentation.
              <br />
              <span className="text-[#2D5AE0]">Get source-backed answers.</span>
            </h1>
            <p className="mt-5 max-w-md text-base leading-relaxed text-[#6B7280]">
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
            <div className="overflow-hidden rounded-xl border border-[#E5E7EB] bg-white shadow-lg shadow-black/5">
              <div className="flex items-center gap-2 border-b border-[#E5E7EB] bg-[#F9FAFB] px-4 py-2.5">
                <div className="flex gap-1.5">
                  <span className="size-2.5 rounded-full bg-[#E5E7EB]" />
                  <span className="size-2.5 rounded-full bg-[#E5E7EB]" />
                  <span className="size-2.5 rounded-full bg-[#E5E7EB]" />
                </div>
                <span className="ml-2 text-xs font-medium text-[#9CA3AF]">terminal</span>
              </div>
              <div className="p-5 font-mono text-[13px] leading-relaxed">
                <div className="flex gap-2">
                  <span className="text-[#059669]">$</span>
                  <span className="text-[#1A1A2E]">How does rate limiting work?</span>
                </div>
                <div className="mt-3 flex gap-2">
                  <span className="text-[#2D5AE0]">&gt;</span>
                  <span className="text-[#6B7280]">Rate limiting uses a sliding window algorithm...</span>
                </div>
                <div className="mt-1 pl-4 text-[#9CA3AF]">
                  Source: api-docs/rate-limiting.md (line 12)
                </div>
                <div className="mt-3 flex gap-2">
                  <span className="text-[#2D5AE0]">&gt;</span>
                  <span className="text-[#6B7280]">The default limit is 100 requests per minute...</span>
                </div>
                <div className="mt-1 pl-4 text-[#9CA3AF]">
                  Source: api-docs/rate-limiting.md (line 24)
                </div>
                <div className="mt-4 flex gap-2">
                  <span className="text-[#2D5AE0]">&gt;</span>
                  <span className="inline-block size-2 bg-[#2D5AE0] animate-pulse" />
                </div>
              </div>
            </div>
            <div className="absolute -bottom-3 -right-3 -z-10 size-full rounded-xl border border-[#E5E7EB] bg-[#F3F4F6]" />
          </div>
        </div>
      </section>

      <section className="border-t border-[#E5E7EB] bg-[#F9FAFB] px-6 lg:px-12">
        <div className="mx-auto max-w-6xl py-16 md:py-20">
          <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
            {features.map((feature, i) => {
              const Icon = feature.icon
              return (
                <Card key={feature.title} className={i === 0 ? "md:col-span-1" : ""}>
                  <CardHeader>
                    <div className="mb-1 flex size-9 items-center justify-center rounded-lg bg-[#EEF2FF]">
                      <Icon className="size-4.5 text-[#2D5AE0]" />
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
