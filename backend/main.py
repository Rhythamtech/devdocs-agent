# fastapi.py
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from agent import DocumentationAgent
from schema import AskRequest, AgentResponse


MAX_PROMPT_LENGTH = 10_000


class AgentService:
    def __init__(self) -> None:
        self._agent: Optional[DocumentationAgent] = None
        self._startup_error: Optional[str] = None

    def init(self) -> None:
        try:
            self._agent = DocumentationAgent()
            self._startup_error = None
        except Exception as e:
            self._agent = None
            self._startup_error = str(e)

    def get(self) -> DocumentationAgent:
        if self._agent is None:
            detail = self._startup_error or "Agent service is not available."
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=detail,
            )
        return self._agent


agent_service = AgentService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    agent_service.init()
    yield


app = FastAPI( title="Documentation Assistant API", version="1.0.0", lifespan=lifespan,)


def error_response( message: str, *, status_code: int, error_code: str, details=None) -> JSONResponse:
    return JSONResponse( status_code=status_code,
                        content={"success": False,
                                 "error": {
                                     "code": error_code,
                                     "message": message,
                                     "details": details, },},
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
    return error_response(
        "Invalid request payload.",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="validation_error",
        details=exc.errors(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return error_response(
        "Internal server error.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="internal_error",
        details=None,
    )


def validate_prompt(prompt: str) -> str:
    if prompt is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prompt is required.",
        )

    cleaned = prompt.strip()

    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prompt cannot be empty.",
        )

    if len(cleaned) > MAX_PROMPT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Prompt is too long. Maximum allowed length is {MAX_PROMPT_LENGTH} characters.",
        )

    return cleaned


@app.get("/health")
def health():
    if agent_service._agent is None:
        return {
            "status": "degraded",
            "agent_available": False,
            "startup_error": agent_service._startup_error,
        }

    return {
        "status": "ok",
        "agent_available": True,
    }


@app.post("/ask",response_model=AgentResponse,status_code=status.HTTP_200_OK)
def ask_docs(req: AskRequest) -> AgentResponse:
    prompt = validate_prompt(req.prompt)
    agent = agent_service.get()

    try:
        return agent.ask(prompt)
    except HTTPException:
        raise
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The agent timed out while processing the request.",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process the prompt.",
        )


@app.post("/ask/stream")
def ask_docs_stream(req: AskRequest):
    prompt = validate_prompt(req.prompt)
    agent = agent_service.get()

    def event_stream():
        try:
            yield "event: status\ndata: started\n\n"

            for chunk in agent.stream(prompt):
                yield chunk

            yield "event: status\ndata: completed\n\n"
        except TimeoutError:
            yield "event: error\ndata: The agent timed out while processing the request.\n\n"
        except Exception:
            yield "event: error\ndata: Failed to process the prompt.\n\n"
        finally:
            yield "event: close\ndata: done\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )