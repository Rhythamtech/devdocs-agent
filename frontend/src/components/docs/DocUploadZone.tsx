"use client"

import React, { useCallback, useState } from "react"
import { motion } from "motion/react"
import { UploadCloud, AlertCircle } from "lucide-react"

interface DocUploadZoneProps {
  onUploadSuccess: (filename: string) => void
  onUploadStart: (filename: string, size: number) => void
  onUploadEnd: (filename: string) => void
  onUploadProgress?: (filename: string, progress: number) => void
  onUploadError?: (filename: string, errorMsg: string) => void
  token: string | null
}

const ALLOWED_EXTENSIONS = [".md", ".txt"]
const MAX_FILE_SIZE = 2 * 1024 * 1024 // 2 MB

function validateFile(file: File): string | null {
  const suffix = file.name.substring(file.name.lastIndexOf(".")).toLowerCase()
  if (!ALLOWED_EXTENSIONS.includes(suffix)) {
    return `${file.name}: unsupported type (only ${ALLOWED_EXTENSIONS.join(", ")})`
  }
  if (file.size > MAX_FILE_SIZE) {
    return `${file.name}: too large (max 2 MB)`
  }
  return null
}

export default function DocUploadZone({
  onUploadSuccess,
  onUploadStart,
  onUploadEnd,
  onUploadProgress,
  onUploadError,
  token,
}: DocUploadZoneProps) {
  const [isDragActive, setIsDragActive] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const uploadFile = useCallback(
    (file: File) => {
      onUploadStart(file.name, file.size)

      const formData = new FormData()
      formData.append("file", file)

      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
      const xhr = new XMLHttpRequest()
      xhr.open("POST", `${API_BASE}/docs/upload`, true)

      if (token) {
        xhr.setRequestHeader("Authorization", `Bearer ${token}`)
      }

      xhr.upload.addEventListener("progress", (event) => {
        if (event.lengthComputable) {
          const pct = Math.round((event.loaded / event.total) * 100)
          onUploadProgress?.(file.name, pct)
        }
      })

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const data = JSON.parse(xhr.responseText)
            onUploadSuccess(data.filename || file.name)
          } catch {
            onUploadSuccess(file.name)
          }
        } else {
          let errorMsg = "Upload failed"
          try {
            const err = JSON.parse(xhr.responseText)
            errorMsg = err.error?.message || err.detail || errorMsg
          } catch {
            // Keep default
          }
          onUploadError?.(file.name, errorMsg)
        }
        onUploadEnd(file.name)
      }

      xhr.onerror = () => {
        onUploadError?.(file.name, "An unexpected error occurred during upload.")
        onUploadEnd(file.name)
      }

      xhr.send(formData)
    },
    [token, onUploadStart, onUploadProgress, onUploadSuccess, onUploadError, onUploadEnd]
  )

  const processFiles = useCallback(
    (files: FileList | File[]) => {
      const skipped: string[] = []

      for (const file of files) {
        const err = validateFile(file)
        if (err) {
          skipped.push(err)
        } else {
          uploadFile(file)
        }
      }

      if (skipped.length > 0) {
        setError(
          skipped.length === files.length
            ? skipped.join("; ")
            : `${skipped.length} file${skipped.length > 1 ? "s" : ""} skipped: ${skipped[0]}${skipped.length > 1 ? ` (+${skipped.length - 1} more)` : ""}`
        )
      } else {
        setError(null)
      }
    },
    [uploadFile]
  )

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragActive(true)
    } else if (e.type === "dragleave") {
      setIsDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFiles(e.dataTransfer.files)
    }
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      processFiles(e.target.files)
      e.target.value = ""
    }
  }

  return (
    <div className="w-full">
      <motion.div
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        animate={{
          borderColor: isDragActive ? "var(--primary)" : "var(--border)",
          backgroundColor: isDragActive ? "var(--primary)" : "var(--card)",
          scale: isDragActive ? 1.01 : 1.0,
          boxShadow: isDragActive
            ? "0 10px 25px -5px color-mix(in srgb, var(--primary) 8%, transparent), 0 8px 10px -6px color-mix(in srgb, var(--primary) 8%, transparent)"
            : "0 1px 3px 0 rgba(0, 0, 0, 0.05)",
        }}
        whileHover={{
          y: -2,
          borderColor: "var(--primary)",
          boxShadow: "0 12px 20px -8px color-mix(in srgb, var(--primary) 8%, transparent)",
        }}
        transition={{ type: "spring", stiffness: 300, damping: 25 }}
        className="relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center transition-all cursor-pointer"
      >
        <input
          type="file"
          id="file-upload-input"
          multiple
          className="absolute inset-0 cursor-pointer opacity-0"
          accept={ALLOWED_EXTENSIONS.join(",")}
          onChange={handleFileInput}
        />

        <div className="flex flex-col items-center">
          <div className="mb-4 flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <UploadCloud className="size-6" />
          </div>
          <p className="text-sm font-semibold text-foreground md:text-base">
            Drag & drop your files here, or <span className="text-primary">browse</span>
          </p>
          <p className="mt-1 text-xs text-muted-foreground/70">
            Markdown (.md) and text (.txt) files. Max 2 MB each. You can select multiple files.
          </p>
        </div>
      </motion.div>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-3 flex items-start gap-2 rounded-xl border border-destructive/20 bg-destructive/5 p-3 text-xs text-destructive"
        >
          <AlertCircle className="size-4 shrink-0 mt-0.5" />
          <div>{error}</div>
        </motion.div>
      )}
    </div>
  )
}
