from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app import crud
from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models import TokenPayload, User

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    # First try to authenticate with JWT token (existing behavior)
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        user = session.get(User, token_data.sub)
        if user and user.is_active:
            return user
    except (InvalidTokenError, ValidationError):
        # If JWT validation fails, try access token authentication
        pass

    # Try to authenticate with long-lived access token
    user = crud.authenticate_with_access_token(session=session, token=token)
    if user:
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        return user

    # If both methods fail, raise authentication error
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials",
    )


def get_current_user_jwt_only(session: SessionDep, token: TokenDep) -> User:
    # Only authenticate with JWT token, not access tokens
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        user = session.get(User, token_data.sub)
        if user and user.is_active:
            return user
    except (InvalidTokenError, ValidationError):
        pass

    # If JWT validation fails, raise authentication error
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials",
    )


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserJwtOnly = Annotated[User, Depends(get_current_user_jwt_only)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user
