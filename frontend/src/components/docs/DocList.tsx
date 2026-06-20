"use client"

import React, { useState } from "react"
import { motion, AnimatePresence } from "motion/react"
import { FileText, Trash2, Loader2, HardDrive } from "lucide-react"
import { DocInfo } from "@/lib/api"

export interface UploadingFile {
  filename: string
  size_bytes: number
  progress: number
  status: "uploading" | "success" | "error"
}

interface DocListProps {
  documents: DocInfo[]
  uploadingFiles?: UploadingFile[]
  onDelete: (filename: string) => Promise<void>
  searchActive?: boolean
}

function formatBytes(bytes: number, decimals = 2) {
  if (bytes === 0) return "0 Bytes"
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ["Bytes", "KB", "MB", "GB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i]
}

function formatTime(isoString: string) {
  try {
    const date = new Date(isoString)
    return date.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })
  } catch {
    return isoString
  }
}

export default function DocList({ documents, uploadingFiles = [], onDelete, searchActive = false }: DocListProps) {
  const [deletingFile, setDeletingFile] = useState<string | null>(null)

  const handleDelete = async (filename: string) => {
    if (deletingFile) return
    setDeletingFile(filename)
    try {
      await onDelete(filename)
    } finally {
      setDeletingFile(null)
    }
  }

  if (documents.length === 0 && uploadingFiles.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border border-border bg-card p-12 text-center shadow-sm">
        <div className="mb-4 flex size-12 items-center justify-center rounded-xl bg-muted text-muted-foreground/70">
          <HardDrive className="size-5" />
        </div>
        <h3 className="text-sm font-semibold text-foreground">
          {searchActive ? "No matching documents found" : "No documents uploaded"}
        </h3>
        <p className="mt-1 max-w-xs text-xs text-muted-foreground/70">
          {searchActive
            ? "Your search term didn't match any filenames in your knowledge base."
            : "Upload READMEs, wikis, or docs in Markdown or Text format to query them with the AI agent."}
        </p>
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[500px] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-border bg-muted text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <th className="px-6 py-4">Document</th>
              <th className="px-6 py-4">Size</th>
              <th className="px-6 py-4">Uploaded At</th>
              <th className="px-6 py-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border text-card-foreground">
            <AnimatePresence initial={false}>
              {uploadingFiles.map((file) => (
                <motion.tr
                  key={`uploading-${file.filename}`}
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="bg-primary/5"
                >
                  <td className="whitespace-nowrap px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <Loader2 className="size-4 animate-spin" />
                      </div>
                      <div className="flex flex-col min-w-0 max-w-[200px] sm:max-w-xs md:max-w-sm">
                        <span className="font-medium text-foreground truncate" title={file.filename}>
                          {file.filename}
                        </span>
                        <span className="text-[10px] text-primary font-semibold uppercase tracking-wider">
                          Uploading...
                        </span>
                      </div>
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-xs text-muted-foreground">
                    {formatBytes(file.size_bytes)}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-xs text-muted-foreground">
                    <div className="flex items-center gap-3 max-w-[150px]">
                      <div className="w-20 bg-secondary rounded-full h-1.5 overflow-hidden">
                        <div
                          className="bg-primary h-1.5 rounded-full transition-all duration-300 ease-out"
                          style={{ width: `${file.progress}%` }}
                        />
                      </div>
                      <span className="text-[10px] font-mono font-bold text-primary">
                        {file.progress}%
                      </span>
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-right">
                    <span className="inline-flex items-center rounded-full bg-primary/10 px-2 py-1 text-xs font-medium text-primary ring-1 ring-inset ring-primary/20">
                      Pending
                    </span>
                  </td>
                </motion.tr>
              ))}
              {documents.map((doc) => (
                <motion.tr
                  key={doc.filename}
                  layout
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, x: -20, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="group hover:bg-muted"
                >
                  <td className="whitespace-nowrap px-6 py-4">
                    <div className="flex items-center gap-3">
                      {doc.filename.toLowerCase().endsWith(".md") ? (
                        <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-orange-500/10 text-orange-500 font-extrabold text-[10px] tracking-tight font-mono border border-orange-500/20 select-none dark:bg-orange-500/15 dark:border-orange-500/25">
                          MD
                        </div>
                      ) : (
                        <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary border border-primary/20">
                          <FileText className="size-4.5" />
                        </div>
                      )}
                      <span className="font-medium text-foreground">{doc.filename}</span>
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-xs text-muted-foreground">
                    {formatBytes(doc.size_bytes)}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-xs text-muted-foreground">
                    {formatTime(doc.uploaded_at)}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-right">
                    <button
                      onClick={() => handleDelete(doc.filename)}
                      disabled={deletingFile !== null}
                      className="inline-flex size-8 items-center justify-center rounded-lg text-muted-foreground/70 hover:bg-destructive/10 hover:text-destructive disabled:opacity-50 transition-colors"
                      title="Delete document"
                    >
                      {deletingFile === doc.filename ? (
                        <Loader2 className="size-4 animate-spin" />
                      ) : (
                        <Trash2 className="size-4" />
                      )}
                    </button>
                  </td>
                </motion.tr>
              ))}
            </AnimatePresence>
          </tbody>
        </table>
      </div>
    </div>
  )
}
