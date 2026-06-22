from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from functools import lru_cache
from pathlib import Path
import re
import urllib.parse

def _find_root() -> Path:
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / ".env").exists():
            return parent
    # If no .env exists (like in a Docker container), find the directory containing project files
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists() or (parent / "main.py").exists():
            return parent
    return current

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
    
    @model_validator(mode="after")
    def resolve_sslip_io_urls(self) -> "Settings":
        if "sslip.io" in self.MONGO_DB_URL:
            try:
                parsed = urllib.parse.urlparse(self.MONGO_DB_URL)
                hostname = parsed.hostname
                if hostname and "sslip.io" in hostname:
                    match = re.search(r"(\d+)-(\d+)-(\d+)-(\d+)\.sslip\.io$", hostname)
                    if match:
                        ip = f"{match.group(1)}.{match.group(2)}.{match.group(3)}.{match.group(4)}"
                        new_netloc = parsed.netloc.replace(hostname, ip)
                        self.MONGO_DB_URL = parsed._replace(netloc=new_netloc).geturl()
            except Exception:
                pass
        return self

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

