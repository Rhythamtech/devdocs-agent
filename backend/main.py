import datetime

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from agent import DocumentationAgent
from utils.auth import hash_password,verify_password,create_access_token,verify_access_token, oauth2_scheme
from core.state import state
from core.config import settings
from schema import UserCreate
from pymongo import AsyncMongoClient
from contextlib import asynccontextmanager
from schema import AskRequest, AgentResponse


MAX_PROMPT_LENGTH = 10_000

@asynccontextmanager
async def lifespan(app: FastAPI):

    try:
        state.agent = DocumentationAgent()
        print("Agent initialized")
        
        state.mongo_client =  AsyncMongoClient(settings.MONGO_DB_URL)
        db = state.mongo_client[settings.MONGO_DATABSE_NAME]
        state.db = db
        
        await db.users.create_index("username", unique=True)
        await db.users.create_index("email", unique=True)
        await db.notes.create_index("owner_id")
        
        yield
        
        state.mongo_client.close()

    except Exception as e:
        state.startup_errors.append(str(e))
        state.agent = None

        print(f"Agent startup failed: {e}")

    yield

    print("Shutdown")


app = FastAPI( title="Documentation Assistant API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def authenticate_user(username: str, password: str):
    is_exist = await state.db.find_one([{"username": username}])
    
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



@app.post("/auth/signup")
async def signup(user: UserCreate, request: Request):
    
    data = user.model_dump()
    data["username"] = data["username"].strip().lower()
    data["email"] = data["email"].strip().lower()


    
    is_exist =  await state.db.users.find_one( {'$or': [{"username": data["username"]}, {"email": data["email"]}]})
    if is_exist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists.",
        )
        
    data.update({"hash_password": hash_password(data["password"])})
    data.update({"created_at": datetime.utcnow()})
        
    result  = await state.db.users.insert_one(data)
    
    return {
        "message": "User created successfully",
        "user_id": str(result.inserted_id),
    }


@app.post("/auth/login")
async def login(request: Request,form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )
    
    token = create_access_token(data={"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer"}


@app.post('/auth/me')
async def me(token: str = Depends(oauth2_scheme)):
    
    exception = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"})
    
    try :
        payload = verify_access_token(token)
        username = payload.sub    
        
        if not username:
            raise exception
    except:
        raise exception

    user =  await state.db.users.find_one( {'$or': [{"username": username}, {"email": username}]})
    
    if not user:
        raise exception
    
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
    }


    
    

@app.get("/health")
def health():
    if state.agent is None:
        return {
            "status": "degraded",
            "agent_available": False,
            "startup_error":"Agent failed to initialize.",
        }

    return {
        "status": "ok",
        "agent_available": True,
    }


@app.post("/ask",response_model=AgentResponse,status_code=status.HTTP_200_OK)
def ask_docs(req: AskRequest) -> AgentResponse:
    prompt = validate_prompt(req.prompt)

    try:
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


@app.post("/ask/stream")
def ask_docs_stream(req: AskRequest):
    prompt = validate_prompt(req.prompt)

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


@app.get("/chats")
def get_chats(session_id: str):
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id is required.",
        )
    try:
        return state.agent.get_chat_history(session_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history.",
        )