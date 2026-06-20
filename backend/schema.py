from pydantic import BaseModel
from typing import Any, Dict, Optional


class ToolResponse(BaseModel):
    content: str
    name: str
    args: Dict[str, Any]


class AgentResponse(BaseModel):
    content: str
    tool_response: Optional[ToolResponse] = None


class AskRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None

class RetryRequest(BaseModel):
    session_id: str

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
