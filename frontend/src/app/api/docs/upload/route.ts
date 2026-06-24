import { NextRequest, NextResponse } from "next/server"

const BACKEND_URL = process.env.API_URL || "http://backend:8000"

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const file = formData.get("file")

    if (!file || typeof file === "string") {
      return NextResponse.json({ detail: "No file provided" }, { status: 400 })
    }

    const auth = request.headers.get("authorization") || ""

    const upstream = new FormData()
    upstream.append("file", file)

    const res = await fetch(`${BACKEND_URL}/docs/upload`, {
      method: "POST",
      headers: { Authorization: auth },
      body: upstream,
    })

    const data = await res.json()

    if (!res.ok) {
      return NextResponse.json(data, { status: res.status })
    }

    return NextResponse.json(data, { status: 201 })
  } catch (err) {
    const message = err instanceof Error ? err.message : "Upload failed"
    return NextResponse.json({ detail: message }, { status: 500 })
  }
}
