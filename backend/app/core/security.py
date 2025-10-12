import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


ALGORITHM = "HS256"


def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def generate_access_token() -> tuple[str, str, str]:
    """
    Generate a new access token with prefix and hash.
    Returns: (token, prefix, token_hash)
    """
    token = secrets.token_urlsafe(32)
    prefix = token[:8]
    token_hash = pwd_context.hash(token)
    return token, prefix, token_hash


def verify_access_token(token: str, token_hash: str) -> bool:
    """Verify an access token against its hash."""
    return pwd_context.verify(token, token_hash)
