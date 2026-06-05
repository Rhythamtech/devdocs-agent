from pydantic import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    OPENAI_BASE_URL: str
    OPENAI_MODEL: str
    AGENTOPS_API_KEY: str

    MONGO_DB_URL: str
    
    ALLOW_ORIGINS: str = "*"
    
    class Config:
        env_file = ".env"
        
        
@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
