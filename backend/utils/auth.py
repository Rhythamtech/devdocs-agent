from fastapi.security import OAuth2PasswordBearer
import jwt
from pwdlib import PasswordHash
from core.config import settings
from datetime import datetime, timedelta, timezone


password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl= "/auth/login")

def hash_password(password:str) ->str :
    return password_hash.hash(password)


def verify_password(plain_password:str, hash_password:str) ->bool:
    return password_hash.verify(plain_password,hash_password)

def create_access_token(data: dict) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_IN_MINUTES)
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def verify_access_token(token: str):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None