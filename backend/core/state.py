
from typing import Optional
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from agent import DocumentationAgent

class AppState:
    agent: Optional[DocumentationAgent] = None
    mongo_client: Optional[AsyncMongoClient] = None
    db: Optional[AsyncDatabase] = None
    startup_errors: list[str] = []



state = AppState()
