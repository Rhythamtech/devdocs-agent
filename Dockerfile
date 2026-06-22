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

# Install system deps
RUN apt-get update -qq \
    && apt-get install -y -qq curl supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install uv + Python deps
RUN pip install --no-cache-dir uv
ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1
COPY backend/pyproject.toml backend/uv.lock ./
RUN touch README.md
RUN uv sync --no-dev --no-install-project

# Copy backend source (flattened into /app/, matches original Dockerfile layout)
COPY backend/ ./

# Copy frontend standalone build
COPY --from=frontend-builder /app/.next/standalone ./frontend/
COPY --from=frontend-builder /app/.next/static ./frontend/.next/static
COPY --from=frontend-builder /app/public ./frontend/public

# Install Node.js for frontend server
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Supervisor config
COPY supervisord.conf /etc/supervisor/supervisord.conf

EXPOSE 3000 8000
CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
