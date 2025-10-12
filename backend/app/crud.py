import uuid
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from app.core.security import (
    generate_access_token,
    get_password_hash,
    verify_access_token,
    verify_password,
)
from app.models import AccessToken, AccessTokenCreate, User, UserCreate, UserUpdate


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user


def create_access_token(
    *, session: Session, token_create: AccessTokenCreate, owner_id: uuid.UUID
) -> tuple[AccessToken, str]:
    """Create a new access token and return both the DB object and the actual token."""
    token, prefix, token_hash = generate_access_token()

    db_obj = AccessToken(
        name=token_create.name,
        token_hash=token_hash,
        prefix=prefix,
        expires_at=token_create.expires_at,
        owner_id=owner_id,
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj, token


def get_access_tokens_by_user(
    *, session: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> list[AccessToken]:
    """Get all access tokens for a user."""
    statement = (
        select(AccessToken)
        .where(AccessToken.owner_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    return list(session.exec(statement).all())


def get_access_token_by_id(
    *, session: Session, token_id: uuid.UUID, user_id: uuid.UUID
) -> AccessToken | None:
    """Get access token by ID, ensuring it belongs to the user."""
    statement = select(AccessToken).where(
        AccessToken.id == token_id, AccessToken.owner_id == user_id
    )
    return session.exec(statement).first()


def authenticate_with_access_token(*, session: Session, token: str) -> User | None:
    """Authenticate a user using an access token."""
    # Get all active tokens (we'll need to check each one as we can't query by hash directly)
    statement = select(AccessToken).where(
        AccessToken.is_active, AccessToken.expires_at > datetime.now(timezone.utc)
    )
    active_tokens = session.exec(statement).all()

    for db_token in active_tokens:
        if verify_access_token(token, db_token.token_hash):
            # Update last used timestamp
            db_token.last_used_at = datetime.now(timezone.utc)
            session.add(db_token)
            session.commit()
            return db_token.owner

    return None


def revoke_access_token(
    *, session: Session, token_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """Revoke (deactivate) an access token."""
    statement = select(AccessToken).where(
        AccessToken.id == token_id, AccessToken.owner_id == user_id
    )
    db_token = session.exec(statement).first()
    if not db_token:
        return False

    db_token.is_active = False
    session.add(db_token)
    session.commit()
    return True
