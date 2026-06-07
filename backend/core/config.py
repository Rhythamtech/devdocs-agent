from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


print(f"Loading settings from {ROOT_DIR / '.env'}")

class Settings(BaseSettings):
    OPENAI_BASE_URL: str
    OPENAI_MODEL: str
    AGENTOPS_API_KEY: str

    MONGO_DB_URL: str
    MONGO_DATABSE_NAME : str
    OPENAI_API_KEYS: str
    
    JWT_SECRET :str
    JWT_EXPIRE_IN_MINUTES : int
    JWT_ALGORITHM :str
        
    ALLOW_ORIGINS: str = "*"
    
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
        
        
@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
