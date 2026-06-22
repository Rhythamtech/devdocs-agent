# ── Backend Dockerfile ────────────────────────────────────────────────────
FROM python:3.12-slim AS backend

WORKDIR /app

RUN pip install --no-cache-dir uv --root-user-action=ignore && \
    rm -rf /root/.cache/pip

COPY backend/pyproject.toml backend/uv.lock ./

RUN UV_SYSTEM_PYTHON=1 uv sync --no-dev && \
    rm -rf /root/.cache/uv

COPY backend/ ./

EXPOSE 8000

CMD ["uv", "run", "fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]
