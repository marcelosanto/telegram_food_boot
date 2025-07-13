import aiosqlite
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from aiosqlite import Connection
from .auth import decode_token, get_user_id_from_username  # Updated import

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")


async def get_db():
    db = await aiosqlite.connect("nutribot.db")
    try:
        yield db
    finally:
        await db.close()


def get_user_id(token: str = Depends(oauth2_scheme), db: Connection = Depends(get_db)):
    payload = decode_token(token)
    username = payload.get("sub")
    user_id = get_user_id_from_username(username, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token or user")
    return user_id


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str):
    return pwd_context.hash(password)
