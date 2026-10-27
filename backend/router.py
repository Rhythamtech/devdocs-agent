import datetime
import contextvars
import json
import time
import uuid
from typing import Annotated, Any, Callable, Iterator
from fastapi import APIRouter, Depends, HTTPException, Request, status, File, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from livekit import api
from psycopg.errors import UniqueViolation
from core.state import state
from core.config import settings
from core.database import AGNO_DB_SCHEMA, AGNO_SESSIONS_TABLE, Database
from core.logger import logger
from schema import UserCreate, AskRequest, AgentResponse, RetryRequest, DocInfo, DocsListResponse, UploadResponse, SessionInfo, SessionsListResponse, VoiceTokenResponse, VoiceTranscriptRequest
from utils.auth import hash_password, verify_password, create_access_token, verify_access_token, oauth2_scheme
from utils.file_handler import save_upload, delete_upload, list_uploads, get_user_upload_dir, initialize_user_docs
from utils.tools import current_user_docs_dir


router = APIRouter()
limiter = state.limiter

SESSIONS_TABLE = f"{AGNO_DB_SCHEMA}.{AGNO_SESSIONS_TABLE}"


MAX_PROMPT_LENGTH = 10_000

AuthException = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired token",
    headers={"WWW-Authenticate": "Bearer"},
)

def get_current_username(token: str = Depends(oauth2_scheme)) -> str:
    payload = verify_access_token(token)
    if not payload:
        raise AuthException
    username = payload.get("sub")
    if not username:
        raise AuthException
    return username

CurrentUser = Annotated[str, Depends(get_current_username)]

async def get_db() -> Database:
    if state.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is not available.",
        )
    return state.db

DatabaseDep = Annotated[Database, Depends(get_db)]


async def ensure_session_access(session_id: str | None, username: str, db: Database) -> None:
    """Reject attempts to reuse a session owned by another user or legacy unowned data."""
    if not session_id:
        return
    agno_row = await db.fetchrow(
        f"SELECT user_id FROM {SESSIONS_TABLE} WHERE session_id = %s",
        (session_id,),
    )
    voice_row = await db.fetchrow(
        "SELECT user_id FROM voice_transcripts WHERE session_id = %s LIMIT 1",
        (session_id,),
    )
    if any(row is not None and row.get("user_id") != username for row in (agno_row, voice_row)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

async def authenticate_user(username: str, password: str, db: Database):
    user = await db.fetchrow(
        "SELECT id, username, email, hash_password FROM users WHERE username = %s",
        (username,),
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    elif not verify_password(password, user["hash_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )
    else:
        return user

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

@router.post("/auth/signup")
@limiter.limit(settings.RATE_LIMIT_SIGNUP)
async def signup(user: UserCreate, request: Request, db: DatabaseDep):
    data = user.model_dump()
    data["username"] = data["username"].strip().lower()
    data["email"] = data["email"].strip().lower()

    is_exist = await db.fetchrow(
        "SELECT 1 FROM users WHERE username = %s OR email = %s",
        (data["username"], data["email"]),
    )
    if is_exist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists.",
        )

    try:
        row = await db.fetchrow(
            """
            INSERT INTO users (username, email, hash_password, created_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (
                data["username"],
                data["email"],
                hash_password(data["password"]),
                datetime.datetime.now(datetime.timezone.utc),
            ),
        )
    except UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists.",
        )

    initialize_user_docs(data["username"])

    return {
        "message": "User created successfully",
        "user_id": str(row["id"]),
    }

@router.post("/auth/login")
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login(request: Request, db: DatabaseDep, form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    # Older accounts may predate the uploads folder or have lost it when the
    # database was reset. Recreate the default document on login so the docs
    # page and the voice agent always have a consistent workspace.
    try:
        initialize_user_docs(user["username"])
    except Exception:
        logger.exception("Failed to initialize document storage for %s", user["username"])

    token = create_access_token(data={"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer"}

@router.get('/auth/me')
async def me(request: Request, db: DatabaseDep, username: CurrentUser):
    user = await db.fetchrow(
        "SELECT id, username, email FROM users WHERE username = %s",
        (username,),
    )
    if not user:
        raise AuthException
    
    return {
        "id": str(user["id"]),
        "username": user["username"],
        "email": user["email"],
    }

@router.get("/health")
@limiter.exempt
async def health(request: Request):
    database_available = False
    if state.db is not None:
        try:
            await state.db.fetchrow("SELECT 1")
            database_available = True
        except Exception:
            logger.warning("Health check could not reach PostgreSQL")

    agent_available = state.agent is not None
    healthy = database_available and agent_available
    result = {
        "status": "ok" if healthy else "degraded",
        "agent_available": agent_available,
        "database_available": database_available,
    }
    if not agent_available:
        result["startup_error"] = "Agent failed to initialize."
    if not database_available:
        result["database_error"] = "Database is unavailable."
    return result

@router.post("/ask", response_model=AgentResponse, status_code=status.HTTP_200_OK)
@limiter.limit(settings.RATE_LIMIT_ASK)
async def ask_docs(
    req: AskRequest,
    request: Request,
    db: DatabaseDep,
    username: CurrentUser,
) -> AgentResponse:
    prompt = validate_prompt(req.prompt)
    await ensure_session_access(req.session_id, username, db)
    user_dir = get_user_upload_dir(username)
    ctx_token = current_user_docs_dir.set(user_dir)
    try:
        return state.agent.ask(prompt, session_id=req.session_id, user_id=username)
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
    finally:
        current_user_docs_dir.reset(ctx_token)

class ContextPropagatingGenerator(Iterator[Any]):
    def __init__(self, generator_func: Callable[..., Iterator[Any]], *args: Any, **kwargs: Any) -> None:
        self.ctx = contextvars.copy_context()
        self.gen = self.ctx.run(generator_func, *args, **kwargs)

    def __iter__(self) -> Iterator[Any]:
        return self

    def __next__(self) -> Any:
        try:
            return self.ctx.run(next, self.gen)
        except StopIteration:
            raise

@router.post("/ask/stream")
@limiter.limit(settings.RATE_LIMIT_ASK_STREAM)
async def ask_docs_stream(
    req: AskRequest,
    request: Request,
    db: DatabaseDep,
    username: CurrentUser,
):
    prompt = validate_prompt(req.prompt)
    await ensure_session_access(req.session_id, username, db)
    user_dir = get_user_upload_dir(username)

    def event_stream():
        ctx_token = current_user_docs_dir.set(user_dir)
        try:
            yield "event: status\ndata: started\n\n"
            for chunk in state.agent.stream(prompt, session_id=req.session_id, user_id=username):
                yield chunk
            yield "event: status\ndata: completed\n\n"
        except TimeoutError:
            yield "event: error\ndata: The agent timed out while processing the request.\n\n"
        except Exception:
            yield "event: error\ndata: Failed to process the prompt.\n\n"
        finally:
            try:
                current_user_docs_dir.reset(ctx_token)
            except ValueError:
                pass
            yield "event: close\ndata: done\n\n"

    return StreamingResponse(
        ContextPropagatingGenerator(event_stream),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@router.get("/chats")
@limiter.limit(settings.RATE_LIMIT_CHATS)
async def get_chats(request: Request, session_id: str, db: DatabaseDep, username: CurrentUser):
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id is required.",
        )
    agno_session = await db.fetchrow(
        f"SELECT 1 FROM {SESSIONS_TABLE} WHERE session_id = %s AND user_id = %s",
        (session_id, username),
    )
    voice_session = await db.fetchrow(
        "SELECT 1 FROM voice_transcripts WHERE session_id = %s AND user_id = %s LIMIT 1",
        (session_id, username),
    )
    if not agno_session and not voice_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

    history = []
    if agno_session:
        try:
            history = state.agent.get_chat_history(session_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve chat history.",
            )
    voice_rows = await db.fetch(
        """
        SELECT message_id, role, content,
               EXTRACT(EPOCH FROM created_at)::DOUBLE PRECISION AS created_at
        FROM voice_transcripts
        WHERE session_id = %s AND user_id = %s
        ORDER BY created_at ASC
        """,
        (session_id, username),
    )
    history.extend(
        {
            "id": row["message_id"],
            "source": "voice",
            "role": row["role"],
            "content": row["content"],
            "created_at": row["created_at"],
        }
        for row in voice_rows
    )
    return sorted(history, key=lambda message: message.get("created_at", 0) or 0)

@router.post("/chats/retry")
@limiter.limit(settings.RATE_LIMIT_RETRY)
async def retry_chat(req: RetryRequest, request: Request, db: DatabaseDep, username: CurrentUser):

    await ensure_session_access(req.session_id, username, db)

    doc = await db.fetchrow(
        f"SELECT runs FROM {SESSIONS_TABLE} WHERE session_id = %s AND user_id = %s",
        (req.session_id, username),
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

    runs = doc.get("runs") or []
    if not isinstance(runs, list) or not runs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No chat history to retry.",
        )

    last_run = runs[-1] if isinstance(runs[-1], dict) else {}

    prompt = None
    messages = last_run.get("messages", [])
    if isinstance(messages, list):
        for msg in messages:
            if isinstance(msg, dict) and msg.get("role") == "user":
                prompt = msg.get("content")
                break

    if not prompt:
        prompt = (last_run.get("input") or {}).get("input_content")

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not retrieve the prompt to retry.",
        )

    result = await db.fetchrow(
        f"""
        UPDATE {SESSIONS_TABLE}
        SET runs = CASE
                WHEN runs IS NULL
                     OR jsonb_typeof(runs) <> 'array'
                     OR jsonb_array_length(runs) = 0
                THEN runs
                ELSE runs - (jsonb_array_length(runs) - 1)
            END,
            updated_at = %s
        WHERE session_id = %s AND user_id = %s
        RETURNING session_id
        """,
        (int(time.time()), req.session_id, username),
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update session history.",
        )

    return {"prompt": prompt}

@router.get("/sessions", response_model=SessionsListResponse)
@limiter.limit("30/minute")
async def list_sessions(request: Request, db: DatabaseDep, username: CurrentUser):
    rows = await db.fetch(
        f"""
        SELECT session_id, COALESCE(MAX(title), session_id) AS title,
               MAX(created_at) AS created_at
        FROM (
            SELECT session_id,
                   COALESCE(session_data->>'session_name', session_id) AS title,
                   created_at
            FROM {SESSIONS_TABLE}
            WHERE user_id = %s
            UNION ALL
            SELECT session_id, 'Voice conversation' AS title,
                   EXTRACT(EPOCH FROM MIN(created_at))::DOUBLE PRECISION AS created_at
            FROM voice_transcripts
            WHERE user_id = %s
            GROUP BY session_id
        ) AS user_sessions
        GROUP BY session_id
        ORDER BY MAX(created_at) DESC
        """,
        (username, username),
    )
    sessions = [
        SessionInfo(
            session_id=row.get("session_id", ""),
            title=row.get("title") or row.get("session_id", "Untitled"),
            created_at=str(row.get("created_at", "")),
        )
        for row in rows
    ]
    return SessionsListResponse(sessions=sessions)

@router.delete("/sessions/{session_id}")
@limiter.limit("30/minute")
async def delete_session(session_id: str, request: Request, db: DatabaseDep, username: CurrentUser):
    await ensure_session_access(session_id, username, db)
    deleted = await db.execute(
        f"DELETE FROM {SESSIONS_TABLE} WHERE session_id = %s AND user_id = %s",
        (session_id, username),
    )
    deleted_voice = await db.execute(
        "DELETE FROM voice_transcripts WHERE session_id = %s AND user_id = %s",
        (session_id, username),
    )
    if deleted == 0 and deleted_voice == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )
    return {"message": "Session deleted."}

@router.delete("/sessions")
@limiter.limit("10/minute")
async def clear_sessions(request: Request, db: DatabaseDep, username: CurrentUser):
    deleted_agno = await db.execute(
        f"DELETE FROM {SESSIONS_TABLE} WHERE user_id = %s",
        (username,),
    )
    deleted_voice = await db.execute(
        "DELETE FROM voice_transcripts WHERE user_id = %s",
        (username,),
    )
    return {"message": f"Deleted {deleted_agno} sessions and {deleted_voice} voice messages."}

@router.post("/voice/transcripts", status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def save_voice_transcript(
    transcript: VoiceTranscriptRequest,
    request: Request,
    db: DatabaseDep,
    username: CurrentUser,
):
    await ensure_session_access(transcript.session_id, username, db)
    await db.execute(
        """
        INSERT INTO voice_transcripts (user_id, session_id, message_id, role, content)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id, session_id, message_id)
        DO UPDATE SET content = EXCLUDED.content
        """,
        (username, transcript.session_id, transcript.message_id, transcript.role, transcript.content),
    )
    return {"message": "Voice transcript saved."}

@router.post("/docs/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_DOCS_UPLOAD)
async def upload_doc(
    request: Request,
    username: CurrentUser,
    file: UploadFile = File(...),
) -> UploadResponse:
    try:
        content = await file.read()
        saved_name = save_upload(username, file.filename, content)
        return UploadResponse(
            filename=saved_name,
            message="File uploaded successfully."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )

@router.get("/docs", response_model=DocsListResponse, status_code=status.HTTP_200_OK)
@limiter.limit(settings.RATE_LIMIT_DOCS_LIST)
def list_docs(
    request: Request,
    username: CurrentUser,
) -> DocsListResponse:
    try:
        uploads = list_uploads(username)
        return DocsListResponse(
            docs=[DocInfo(**d) for d in uploads]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )

@router.delete("/docs/{filename}", status_code=status.HTTP_200_OK)
@limiter.limit(settings.RATE_LIMIT_DOCS_DELETE)
def delete_doc(
    filename: str,
    request: Request,
    username: CurrentUser,
):
    try:
        delete_upload(username, filename)
        return {"message": f"File '{filename}' deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )


@router.post("/voice/token", response_model=VoiceTokenResponse, status_code=status.HTTP_200_OK)
@limiter.limit(settings.RATE_LIMIT_VOICE_TOKEN)
def create_voice_token(request: Request, username: CurrentUser) -> VoiceTokenResponse:
    """Mint a short-lived LiveKit token and dispatch the voice agent to a room."""
    if not all(
        (
            settings.LIVEKIT_URL,
            settings.LIVEKIT_API_KEY,
            settings.LIVEKIT_API_SECRET,
            settings.DEEPGRAM_API_KEY,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Voice is not configured. Set LIVEKIT_URL, LIVEKIT_API_KEY, "
                "LIVEKIT_API_SECRET, and DEEPGRAM_API_KEY."
            ),
        )

    room_name = f"devdocs-voice-{uuid.uuid4().hex}"

    try:
        token = (
            api.AccessToken(
                settings.LIVEKIT_API_KEY,
                settings.LIVEKIT_API_SECRET,
            )
            .with_identity(username)
            .with_name(username)
            .with_ttl(datetime.timedelta(minutes=settings.VOICE_TOKEN_TTL_MINUTES))
            .with_grants(api.VideoGrants(room_join=True, room=room_name))
            .with_room_config(
                api.RoomConfiguration(
                    agents=[
                        api.RoomAgentDispatch(
                            agent_name=settings.VOICE_AGENT_NAME,
                            metadata=json.dumps({"username": username}),
                        )
                    ]
                )
            )
            .to_jwt()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create voice token: {str(e)}",
        )

    return VoiceTokenResponse(
        server_url=settings.LIVEKIT_URL,
        participant_token=token,
        room_name=room_name,
    )
