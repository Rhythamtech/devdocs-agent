import type { NextConfig } from "next";

// Local dev proxies to the FastAPI server on the host; the Docker image
// resolves the Compose service name instead.
const backendUrl =
  process.env.BACKEND_INTERNAL_URL ??
  (process.env.NODE_ENV === "development"
    ? "http://localhost:8000"
    : "http://backend:8000");

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      { source: "/auth/:path*", destination: `${backendUrl}/auth/:path*` },
      { source: "/ask/:path*", destination: `${backendUrl}/ask/:path*` },
      { source: "/chats/:path*", destination: `${backendUrl}/chats/:path*` },
      { source: "/sessions/:path*", destination: `${backendUrl}/sessions/:path*` },
      { source: "/voice/:path*", destination: `${backendUrl}/voice/:path*` },
      { source: "/api/docs", destination: `${backendUrl}/docs` },
      { source: "/api/docs/:path*", destination: `${backendUrl}/docs/:path*` },
    ]
  },
};

export default nextConfig;
