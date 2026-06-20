import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from pymongo.asynchronous.database import AsyncDatabase
from core.state import state
from core.config import settings
from schema import UserCreate, AskRequest, AgentResponse, RetryRequest
from utils.auth import hash_password, verify_password, create_access_token, verify_access_token, oauth2_scheme

router = APIRouter()
limiter = state.limiter


MAX_PROMPT_LENGTH = 10_000

async def get_db() -> AsyncDatabase:
    if state.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is not available.",
        )
    return state.db

DatabaseDep = Annotated[AsyncDatabase, Depends(get_db)]

async def authenticate_user(username: str, password: str, db: AsyncDatabase):
    is_exist = await db.users.find_one({"username": username})
    
    if not is_exist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
        
    elif not verify_password(password, is_exist["hash_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )
    else:
        return is_exist

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

    is_exist = await db.users.find_one({'$or': [{"username": data["username"]}, {"email": data["email"]}]})
    if is_exist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists.",
        )
        
    data.update({"hash_password": hash_password(data["password"])})
    data.update({"created_at": datetime.datetime.now()})
        
    result = await db.users.insert_one(data)
    
    return {
        "message": "User created successfully",
        "user_id": str(result.inserted_id),
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
    
    token = create_access_token(data={"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer"}

@router.get('/auth/me')
async def me(request: Request, db: DatabaseDep, token: str = Depends(oauth2_scheme)):
    exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    
    try:
        payload = verify_access_token(token)
        username = payload.get("sub")    
        if not username:
            raise exception
    except:
        raise exception

    user = await db.users.find_one({'$or': [{"username": username}, {"email": username}]})
    if not user:
        raise exception
    
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
    }

@router.get("/health")
@limiter.exempt
def health(request: Request):
    if state.agent is None:
        return {
            "status": "degraded",
            "agent_available": False,
            "startup_error": "Agent failed to initialize.",
        }
    return {
        "status": "ok",
        "agent_available": True,
    }

@router.post("/ask", response_model=AgentResponse, status_code=status.HTTP_200_OK)
@limiter.limit(settings.RATE_LIMIT_ASK)
def ask_docs(req: AskRequest, request: Request, token: str = Depends(oauth2_scheme)) -> AgentResponse:
    prompt = validate_prompt(req.prompt)
    user = verify_access_token(token)

    try:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        return state.agent.ask(prompt, session_id=req.session_id)
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

@router.post("/ask/stream")
@limiter.limit(settings.RATE_LIMIT_ASK_STREAM)
def ask_docs_stream(req: AskRequest, request: Request, token: str = Depends(oauth2_scheme)):
    prompt = validate_prompt(req.prompt)
    user = verify_access_token(token)

    try:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        def event_stream():
            try:
                yield "event: status\ndata: started\n\n"
                for chunk in state.agent.stream(prompt, session_id=req.session_id):
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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

@router.get("/chats")
@limiter.limit(settings.RATE_LIMIT_CHATS)
def get_chats(request: Request, session_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_access_token(token)
    
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id is required.",
        )
    try:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        return state.agent.get_chat_history(session_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history.",
        )

@router.post("/chats/retry")
@limiter.limit(settings.RATE_LIMIT_RETRY)
async def retry_chat(req: RetryRequest, request: Request, db: DatabaseDep, token: str = Depends(oauth2_scheme)):
    user = verify_access_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    
    doc = await db.agno_sessions.find_one({"session_id": req.session_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )
    
    runs = doc.get("runs", [])
    if not runs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No chat history to retry.",
        )
    
    last_run = runs[-1]
    
    prompt = None
    messages = last_run.get("messages", [])
    if messages:
        for msg in messages:
            if msg.get("role") == "user":
                prompt = msg.get("content")
                break
    
    if not prompt:
        prompt = last_run.get("input", {}).get("input_content")
        
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not retrieve the prompt to retry.",
        )
    
    result = await db.agno_sessions.update_one(
        {"session_id": req.session_id},
        {"$pop": {"runs": 1}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update session history.",
        )
        
    return {"prompt": prompt}

