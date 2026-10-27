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

# Read a setting from the environment, falling back to .env, without sourcing it.
env_value() {
  local key="$1"
  local value="${!key:-}"
  if [ -z "$value" ]; then
    value="$(grep -E "^[[:space:]]*${key}[[:space:]]*=" "$ROOT/.env" 2>/dev/null \
      | tail -1 | cut -d= -f2- | tr -d '"' | tr -d "'" | xargs || true)"
  fi
  printf '%s' "$value"
}

VOICE_ENABLED=true
for key in LIVEKIT_URL LIVEKIT_API_KEY LIVEKIT_API_SECRET DEEPGRAM_API_KEY; do
  if [ -z "$(env_value "$key")" ]; then
    VOICE_ENABLED=false
    break
  fi
done

# ── postgres reachability ──────────────────────────────────────────────────
PG_URL="$(env_value POSTGRES_URL)"
if [ -z "$PG_URL" ]; then
  PG_URL="postgresql://devdocs:devdocs@localhost:5432/devdocs"
fi
PG_HOST=""
PG_PORT="5432"
if command -v python3 >/dev/null 2>&1; then
  PG_INFO="$(python3 -c "import sys; from urllib.parse import urlsplit; u = urlsplit(sys.argv[1]); print(u.hostname or '', u.port or 5432)" "$PG_URL" 2>/dev/null)"
  PG_HOST="${PG_INFO%% *}"
  PG_PORT="${PG_INFO##* }"
fi
if [ -n "$PG_HOST" ]; then
  if [ "$PG_HOST" = "localhost" ] || [ "$PG_HOST" = "127.0.0.1" ]; then
    if (exec 3<>"/dev/tcp/$PG_HOST/$PG_PORT") 2>/dev/null; then
      log "PostgreSQL reachable at $PG_HOST:$PG_PORT"
    else
      warn "PostgreSQL is not reachable at $PG_HOST:$PG_PORT (from POSTGRES_URL)."
      warn "Start the bundled database with: docker compose up -d postgres"
      exit 1
    fi
  else
    log "Skipping local PostgreSQL check (POSTGRES_URL points at $PG_HOST)."
  fi
fi

# ── install deps if needed ─────────────────────────────────────────────────
log "Syncing backend dependencies (uv sync)…"
(cd "$BACKEND" && uv sync --quiet)

log "Installing frontend dependencies (npm install)…"
(cd "$FRONTEND" && npm install --silent)

# ── cleanup on exit ────────────────────────────────────────────────────────
cleanup() {
  log "Shutting down…"
  kill "$BACKEND_PID" "$FRONTEND_PID" ${VOICE_PID:+"$VOICE_PID"} 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" ${VOICE_PID:+"$VOICE_PID"} 2>/dev/null || true
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

# ── start voice worker (optional) ──────────────────────────────────────────
VOICE_PID=""
if [ "$VOICE_ENABLED" = true ]; then
  log "Starting LiveKit voice worker …"
  (cd "$BACKEND" && uv run python -m voice.agent dev) &
  VOICE_PID=$!
else
  warn "Voice disabled – set LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET and DEEPGRAM_API_KEY in .env to enable it."
fi

log "Servers running. Press Ctrl+C to stop."
if [ -n "$VOICE_PID" ]; then
  wait "$BACKEND_PID" "$FRONTEND_PID" "$VOICE_PID"
else
  wait "$BACKEND_PID" "$FRONTEND_PID"
fi
