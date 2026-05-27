from pydantic import BaseModel

class ToolResponse(BaseModel):
    content: str
    name : str
    args : dict


class AgentResponse(BaseModel):
   
    content: str
    tool_response: ToolResponse | None = None