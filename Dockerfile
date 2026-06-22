# ── Stage 1: Build frontend (Next.js) ─────────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG NEXT_PUBLIC_API_URL=
ARG NEXT_PUBLIC_MOCK_MODE=false
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_MOCK_MODE=$NEXT_PUBLIC_MOCK_MODE
RUN npm run build

# ── Stage 2: Runtime (backend + frontend) ────────────────────────────────
FROM python:3.12-slim
WORKDIR /app

# Install system deps (curl, supervisor, Node.js for Next.js standalone)
RUN apt-get update -qq \
    && apt-get install -y -qq curl supervisor \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y -qq nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV PATH="/app/.venv/bin:$PATH"

# Synchronize python dependencies
COPY backend/pyproject.toml backend/uv.lock ./
RUN touch README.md \
    && uv venv .venv \
    && uv sync --no-dev --no-install-project

# Copy backend source code
COPY backend/ ./

# Copy frontend standalone build files from Stage 1
COPY --from=frontend-builder /app/.next/standalone ./frontend/
COPY --from=frontend-builder /app/.next/static ./frontend/.next/static
COPY --from=frontend-builder /app/public ./frontend/public

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/supervisord.conf

# Expose ports for both services (for single-container fallback)
EXPOSE 3000 8000

# Start supervisor
CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
