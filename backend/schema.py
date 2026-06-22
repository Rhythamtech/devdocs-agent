from pydantic import BaseModel
from typing import Any, Optional


class ToolResponse(BaseModel):
    content: str
    name: str
    args: dict[str, Any]


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

class DocInfo(BaseModel):
    filename: str
    size_bytes: int
    uploaded_at: str

class DocsListResponse(BaseModel):
    docs: list[DocInfo]

class UploadResponse(BaseModel):
    filename: str
    message: str

class SessionInfo(BaseModel):
    session_id: str
    title: str
    created_at: str

class SessionsListResponse(BaseModel):
    sessions: list[SessionInfo]

