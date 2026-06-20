from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from agent import DocumentationAgent
from core.state import state
from core.config import settings
from core.logger import logger
from pymongo import AsyncMongoClient
from fastapi import HTTPException
from contextlib import asynccontextmanager
from router import router
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Agent init (non-fatal — degraded mode if it fails) ─────────────────
    try:
        state.agent = DocumentationAgent()
        logger.info("Agent initialized")
    except Exception as e:
        state.startup_errors.append(str(e))
        state.agent = None
        logger.error(f"Agent startup failed: {e}")

    # ── Database init (runs regardless of agent status) ────────────────────
    try:
        state.mongo_client = AsyncMongoClient(settings.MONGO_DB_URL)
        state.db = state.mongo_client[settings.MONGO_DATABASE_NAME]

        await state.db.users.create_index("username", unique=True)
        await state.db.users.create_index("email", unique=True)

        logger.info("Database connected")
    except Exception as e:
        state.startup_errors.append(str(e))
        state.db = None
        logger.error(f"Database startup failed: {e}")

    yield

    # ── Shutdown ───────────────────────────────────────────────────────────
    if state.mongo_client is not None:
        await state.mongo_client.close()
    logger.info("Shutdown")

app = FastAPI(title="Documentation Assistant API", version="1.0.0", lifespan=lifespan)
app.state.limiter = state.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def error_response(message: str, *, status_code: int, error_code: str, details=None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
                "details": details,
            },
        },
    )

@app.exception_handler(status.HTTP_404_NOT_FOUND)
async def not_found_exception_handler(request: Request, exc: Exception):
    return error_response(
        "Resource not found.",
        status_code=status.HTTP_404_NOT_FOUND,
        error_code="not_found",
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return error_response(
        detail,
        status_code=exc.status_code,
        error_code="http_error",
        details=None if isinstance(exc.detail, str) else exc.detail,
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error: {exc.errors()}")
    return error_response(
        "Invalid request payload.",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="validation_error",
        details=exc.errors(),
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception occurred")
    return error_response(
        "Internal server error.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="internal_error",
        details=None,
    )

app.include_router(router)
