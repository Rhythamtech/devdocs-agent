# Stage 1: Build virtual environment
FROM python:3.12-slim AS builder

# Set env variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Create virtual environment and sync dependencies
# Note: --no-dev excludes development dependencies.
RUN uv venv .venv && \
    uv sync --no-dev --no-install-project

# Stage 2: Runtime image
FROM python:3.12-slim AS runtime

# Set env variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Install runtime dependencies (like curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -m -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy backend code
COPY --chown=appuser:appuser . .

# Set uploads folder permission
RUN mkdir -p /app/docs/uploads && chown -R appuser:appuser /app/docs/uploads

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run uvicorn with proxy root path set to /api
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--root-path", "/api"]
