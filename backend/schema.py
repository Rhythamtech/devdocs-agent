from pydantic import BaseModel, Field
from typing import Any, Literal, Optional


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

class VoiceTokenResponse(BaseModel):
    server_url: str
    participant_token: str
    room_name: str


class VoiceTranscriptRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=255)
    message_id: str = Field(min_length=1, max_length=255)
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=10_000)
