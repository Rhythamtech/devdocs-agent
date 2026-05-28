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
