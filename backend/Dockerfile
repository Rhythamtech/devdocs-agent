# ── Backend Dockerfile ────────────────────────────────────────────────────
FROM python:3.12-slim AS backend

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency manifest first for layer caching
COPY backend/pyproject.toml backend/uv.lock ./

# Install dependencies into the system Python (no venv needed inside Docker)
RUN uv sync --no-dev --system

# Copy the rest of the source
COPY backend/ ./

EXPOSE 8000

CMD ["uv", "run", "fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]
