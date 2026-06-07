
from typing import Optional
from pymongo import AsyncMongoClient
from agent import DocumentationAgent

class AppState:
    agent: Optional[DocumentationAgent] = None
    mongo_client : AsyncMongoClient
    startup_errors: list[str] = []



state = AppState()