from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT_DIR / ".env"
if not ENV_FILE.exists():
    # Inside the Docker image the backend lives at /app, so a mounted .env
    # would be at /app/.env rather than the repository root.
    ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


print(f"Loading settings from {ENV_FILE}")

class Settings(BaseSettings):
    OPENAI_BASE_URL: str 
    OPENAI_MODEL: str 
    AGENTOPS_API_KEY: str 

    POSTGRES_URL: str
    POSTGRES_CONNECT_TIMEOUT: int = 10
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
    RATE_LIMIT_VOICE_TOKEN: str = "10/minute"
    VOICE_TOKEN_TTL_MINUTES: int = 10

    # Voice (LiveKit + Deepgram). Empty values keep voice disabled without
    # preventing the text-only app from starting.
    LIVEKIT_URL: str = ""
    LIVEKIT_API_KEY: str = ""
    LIVEKIT_API_SECRET: str = ""
    DEEPGRAM_API_KEY: str = ""
    VOICE_AGENT_NAME: str = "devdocs-voice"
    VOICE_LLM_MODEL: str = "google/gemma-4-31b-it"
    VOICE_STT_MODEL: str = "flux-general-en"
    VOICE_TTS_MODEL: str = "aura-2-thalia-en"
    VOICE_KEYTERMS: str = "DevDocs,Agno,FastAPI,PostgreSQL,LiveKit,Deepgram"
    
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
        
        
@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()

