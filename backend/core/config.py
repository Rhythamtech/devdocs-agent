from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


print(f"Loading settings from {ROOT_DIR / '.env'}")

class Settings(BaseSettings):
    OPENAI_BASE_URL: str = Field(..., description="OpenAI base URL")
    OPENAI_MODEL: str = Field(..., description="OpenAI model")
    AGENTOPS_API_KEY: str = Field(..., description="AgentOps API key")

    MONGO_DB_URL: str = Field(..., description="MongoDB URL")
    MONGO_DATABASE_NAME : str = Field(..., description="MongoDB database name")
    OPENAI_API_KEYS: str = Field(..., description= "Comma separated OpenAI API keys")
    
    JWT_SECRET :str = Field(..., description="JWT secret")
    JWT_EXPIRE_IN_MINUTES : int = Field(..., description="JWT expire in minutes")
    JWT_ALGORITHM :str = Field(..., description="JWT algorithm", default='HS256')
        
    ALLOW_ORIGINS: str = Field(..., description="Allowed origins", default="*")
    
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

