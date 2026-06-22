from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

def _find_root() -> Path:
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / ".env").exists():
            return parent
    return current.parents[2]

ROOT_DIR = _find_root()


class Settings(BaseSettings):
    OPENAI_BASE_URL: str 
    OPENAI_MODEL: str 
    AGENTOPS_API_KEY: str 

    MONGO_DB_URL: str 
    MONGO_DATABASE_NAME : str 
    OPENAI_API_KEYS: str 
    
    JWT_SECRET :str 
    JWT_EXPIRE_IN_MINUTES : int 
    JWT_ALGORITHM :str 
        
    ALLOW_ORIGINS: str = "*"

    RATE_LIMIT_SIGNUP: str = "5/minute"
    RATE_LIMIT_LOGIN: str = "10/minute"
    RATE_LIMIT_ASK: str = "20/minute"
    RATE_LIMIT_ASK_STREAM: str = "10/minute"
    RATE_LIMIT_CHATS: str = "30/minute"
    RATE_LIMIT_GLOBAL: str = "60/minute"
    RATE_LIMIT_RETRY: str = "3/minute;15/day"

    UPLOADS_ROOT: str = "docs/uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 2097152  # 2 MB
    RATE_LIMIT_DOCS_UPLOAD: str = "5/minute"
    RATE_LIMIT_DOCS_LIST: str = "30/minute"
    RATE_LIMIT_DOCS_DELETE: str = "10/minute"
    
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
        
        
@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()

