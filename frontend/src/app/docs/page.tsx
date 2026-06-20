"use client"

import React, { useEffect, useState, useCallback } from "react"
import { ProtectedRoute } from "@/components/layout/ProtectedRoute"
import { useAuth } from "@/contexts/AuthContext"
import { listDocuments, deleteDocument, DocInfo } from "@/lib/api"
import DocUploadZone from "@/components/docs/DocUploadZone"
import DocList, { UploadingFile } from "@/components/docs/DocList"
import { AlertCircle, HelpCircle, Search, HardDrive, ShieldCheck } from "lucide-react"
import { toast } from "sonner"

export default function DocsPage() {
  const { token, isAuthenticated } = useAuth()
  const [documents, setDocuments] = useState<DocInfo[]>([])
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")

  const loadDocs = useCallback(async () => {
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      const data = await listDocuments(token)
      setDocuments(data)
    } catch (err: any) {
      setError(err.message || "Failed to load documents.")
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    if (isAuthenticated) {
      loadDocs()
    }
  }, [isAuthenticated, loadDocs])

  const handleDelete = async (filename: string) => {
    const toastId = toast.loading(`Deleting ${filename}...`)
    try {
      await deleteDocument(filename, token)
      setDocuments((prev) => prev.filter((d) => d.filename !== filename))
      toast.success(`${filename} deleted successfully`, { id: toastId })
    } catch (err: any) {
      toast.error(err.message || `Failed to delete ${filename}`, { id: toastId })
    }
  }

  const handleUploadStart = (filename: string, size: number) => {
    setUploadingFiles((prev) => [
      ...prev,
      { filename, size_bytes: size, progress: 0, status: "uploading" },
    ])
    toast.loading(`Uploading ${filename}...`, { id: filename })
  }

  const handleUploadProgress = (filename: string, progress: number) => {
    setUploadingFiles((prev) =>
      prev.map((f) => (f.filename === filename ? { ...f, progress } : f))
    )
  }

  const handleUploadSuccess = (filename: string) => {
    setUploadingFiles((prev) =>
      prev.map((f) =>
        f.filename === filename ? { ...f, progress: 100, status: "success" } : f
      )
    )
    toast.success(`${filename} uploaded successfully`, { id: filename })
    loadDocs()
  }

  const handleUploadError = (filename: string, errorMsg: string) => {
    setUploadingFiles((prev) =>
      prev.map((f) =>
        f.filename === filename ? { ...f, status: "error" } : f
      )
    )
    toast.error(`Failed to upload ${filename}: ${errorMsg}`, { id: filename })
  }

  const handleUploadEnd = (filename: string) => {
    setTimeout(() => {
      setUploadingFiles((prev) => prev.filter((f) => f.filename !== filename))
    }, 1000)
  }

  const totalDocs = documents.length
  const totalSize = documents.reduce((acc, d) => acc + d.size_bytes, 0)
  
  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 Bytes"
    const k = 1024
    const sizes = ["Bytes", "KB", "MB"]
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i]
  }

  const filteredDocuments = documents.filter((doc) =>
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <ProtectedRoute>
      <div className="flex-1 bg-background py-10 px-4 md:px-8">
        <div className="mx-auto max-w-4xl space-y-8">
          {/* Header */}
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl">
                My Knowledge Base
              </h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Manage documents the AI agent searches across.
              </p>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-border bg-card p-5 shadow-sm transition-all hover:shadow-md hover:border-primary/20">
              <div className="flex items-center justify-between">
                <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/70">
                  Total Documents
                </div>
                <HardDrive className="size-4 text-primary" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-foreground">{totalDocs}</span>
                <span className="text-xs text-muted-foreground">files uploaded</span>
              </div>
            </div>

            <div className="rounded-2xl border border-border bg-card p-5 shadow-sm transition-all hover:shadow-md hover:border-primary/20">
              <div className="flex items-center justify-between">
                <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/70">
                  Storage Space
                </div>
                <Search className="size-4 text-primary" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-foreground">{formatBytes(totalSize)}</span>
                <span className="text-xs text-muted-foreground">of 10 MB used</span>
              </div>
            </div>

            <div className="rounded-2xl border border-border bg-card p-5 shadow-sm transition-all hover:shadow-md hover:border-primary/20">
              <div className="flex items-center justify-between">
                <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/70">
                  Security Scope
                </div>
                <ShieldCheck className="size-4 text-primary" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-sm font-bold text-primary uppercase tracking-wider font-mono">Private</span>
                <span className="text-xs text-muted-foreground">user isolated</span>
              </div>
            </div>
          </div>

          {/* Info callout */}
          <div className="flex items-start gap-3 rounded-2xl border border-primary/20 bg-primary/5 p-4 text-sm text-primary">
            <HelpCircle className="size-5 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">User Uploads Scoping</p>
              <p className="mt-1 text-muted-foreground leading-relaxed">
                The assistant answers questions <strong>exclusively</strong> using documents you upload below. Your uploads are private and isolated to your profile.
              </p>
            </div>
          </div>

          {/* Upload Zone */}
          <div className="space-y-3">
            <h2 className="text-lg font-semibold text-foreground">Upload Wikis &amp; READMEs</h2>
            <DocUploadZone
              token={token}
              onUploadSuccess={handleUploadSuccess}
              onUploadStart={handleUploadStart}
              onUploadProgress={handleUploadProgress}
              onUploadError={handleUploadError}
              onUploadEnd={handleUploadEnd}
            />
          </div>

          {/* Document List */}
          <div className="space-y-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-lg font-semibold text-foreground">All Uploaded Files</h2>
              <div className="relative w-full sm:max-w-xs">
                <input
                  type="text"
                  placeholder="Search documents..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full rounded-xl border border-border bg-card py-1.5 pl-9 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/15 transition-all"
                />
                <Search className="absolute left-3 top-2.5 size-4 text-muted-foreground/70" />
              </div>
            </div>

            {loading && documents.length === 0 ? (
              <div className="flex items-center justify-center py-12 text-sm text-muted-foreground/70">
                <div className="flex gap-1 mr-2">
                  <span className="size-1.5 rounded-full bg-primary animate-pulse" style={{ animationDelay: "0ms" }} />
                  <span className="size-1.5 rounded-full bg-primary animate-pulse" style={{ animationDelay: "200ms" }} />
                  <span className="size-1.5 rounded-full bg-primary animate-pulse" style={{ animationDelay: "400ms" }} />
                </div>
                Loading documents…
              </div>
            ) : error ? (
              <div className="flex items-start gap-2 rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-xs text-destructive">
                <AlertCircle className="size-4 shrink-0 mt-0.5" />
                <div>{error}</div>
              </div>
            ) : (
              <DocList
                documents={filteredDocuments}
                uploadingFiles={uploadingFiles}
                onDelete={handleDelete}
                searchActive={searchQuery.trim().length > 0}
              />
            )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  )
}
