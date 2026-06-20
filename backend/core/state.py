
from typing import Optional
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
from agent import DocumentationAgent
from utils.auth import verify_access_token
from core.config import settings

def get_rate_limit_key(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            payload = verify_access_token(auth.split(" ", 1)[1])
            return payload.get("sub") or get_remote_address(request)
        except Exception:
            pass
    return get_remote_address(request)

class AppState:
    agent: Optional[DocumentationAgent] = None
    mongo_client: Optional[AsyncMongoClient] = None
    db: Optional[AsyncDatabase] = None
    limiter: Limiter = Limiter(key_func=get_rate_limit_key, default_limits=[settings.RATE_LIMIT_GLOBAL])
    startup_errors: list[str] = []



state = AppState()
