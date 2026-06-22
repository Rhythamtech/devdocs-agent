# ── Backend Dockerfile ────────────────────────────────────────────────────
FROM python:3.12-slim AS backend

WORKDIR /app

# Install uv + curl (for healthcheck)
RUN apt-get update -qq && apt-get install -y -qq curl && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Set environment variables for uv to install to system Python and compile bytecode
ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1

# Copy dependency manifest first for layer caching
COPY backend/pyproject.toml backend/uv.lock ./

# Touch a dummy README.md because pyproject.toml references it
RUN touch README.md

# Install dependencies into the system Python (no venv needed inside Docker)
RUN uv sync --no-dev --no-install-project

# Copy the rest of the source
COPY backend/ ./

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]
