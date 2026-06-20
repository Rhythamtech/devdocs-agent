#!/usr/bin/env bash
# start.sh — run backend + frontend together
# Usage: ./start.sh
# Press Ctrl+C to stop both.

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

# Colours
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[start]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC} $*"; }

# ── pre-flight checks ───────────────────────────────────────────────────────
command -v uv   >/dev/null 2>&1 || { warn "uv not found – install from https://github.com/astral-sh/uv"; exit 1; }
command -v node >/dev/null 2>&1 || { warn "node not found"; exit 1; }
command -v npm  >/dev/null 2>&1 || { warn "npm not found"; exit 1; }

# ── env check ──────────────────────────────────────────────────────────────
if [ ! -f "$ROOT/.env" ]; then
  warn ".env file not found at project root. Copy .env.example and fill in values."
  exit 1
fi

# ── install deps if needed ─────────────────────────────────────────────────
log "Syncing backend dependencies (uv sync)…"
(cd "$BACKEND" && uv sync --quiet)

log "Installing frontend dependencies (npm install)…"
(cd "$FRONTEND" && npm install --silent)

# ── cleanup on exit ────────────────────────────────────────────────────────
cleanup() {
  log "Shutting down…"
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup INT TERM

# ── start backend ──────────────────────────────────────────────────────────
log "Starting FastAPI backend on http://localhost:8000 …"
(cd "$BACKEND" && uv run fastapi dev main.py --host 0.0.0.0 --port 8000) &
BACKEND_PID=$!

# ── start frontend ─────────────────────────────────────────────────────────
log "Starting Next.js frontend on http://localhost:3000 …"
(cd "$FRONTEND" && npm run dev) &
FRONTEND_PID=$!

log "Both servers running. Press Ctrl+C to stop."
wait "$BACKEND_PID" "$FRONTEND_PID"
