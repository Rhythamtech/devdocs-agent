
from typing import Optional

from agent import DocumentationAgent

class AppState:
    agent: Optional[DocumentationAgent] = None
    startup_errors: list[str] = []


state = AppState()