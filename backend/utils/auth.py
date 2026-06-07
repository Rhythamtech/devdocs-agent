from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from datetime import time, timedelta, timezone


password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl= "/auth/login")

def hash_password(password:str) ->str :
    return password_hash.hash(password)


def verify_password(plain_paswword:str, hash_password:str) ->bool:
    
    return password_hash.verify(plain_paswword,hash_password)

