from jose import JWTError, jwt
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from passlib.context import CryptContext
from ..config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
import aiosqlite

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_user_id_from_username(username: str, db: aiosqlite.Connection):
    query = await db.execute("SELECT user_id FROM users WHERE username = ?", (username,))
    user = await query.fetchone()
    return user[0] if user else None
