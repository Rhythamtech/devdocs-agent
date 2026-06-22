import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/auth/:path*",
        destination: "http://localhost:8000/auth/:path*",
      },
      {
        source: "/ask/:path*",
        destination: "http://localhost:8000/ask/:path*",
      },
      {
        source: "/chats/:path*",
        destination: "http://localhost:8000/chats/:path*",
      },
      {
        source: "/sessions/:path*",
        destination: "http://localhost:8000/sessions/:path*",
      },
      {
        source: "/docs/:path*",
        destination: "http://localhost:8000/docs/:path*",
      },
      {
        source: "/health",
        destination: "http://localhost:8000/health",
      },
    ]
  },
};

export default nextConfig;
