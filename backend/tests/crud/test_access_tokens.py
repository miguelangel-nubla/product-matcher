import uuid
from datetime import datetime, timezone, timedelta

import pytest
from sqlmodel import Session

from app import crud
from app.models import AccessTokenCreate, User
from tests.utils.user import create_random_user


def test_create_access_token(db: Session) -> None:
    user = create_random_user(db)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    token_create = AccessTokenCreate(name="Test Token", expires_at=expires_at)

    db_token, token = crud.create_access_token(
        session=db, token_create=token_create, owner_id=user.id
    )

    assert db_token.name == "Test Token"
    assert db_token.is_active is True
    assert db_token.owner_id == user.id
    assert db_token.expires_at.replace(tzinfo=timezone.utc) == expires_at
    assert len(db_token.prefix) == 8
    assert len(token) > 0
    assert db_token.prefix == token[:8]


def test_create_access_token_with_expiration(db: Session) -> None:
    user = create_random_user(db)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    token_create = AccessTokenCreate(
        name="Expiring Token", expires_at=expires_at
    )

    db_token, token = crud.create_access_token(
        session=db, token_create=token_create, owner_id=user.id
    )

    assert db_token.expires_at.replace(tzinfo=timezone.utc) == expires_at


def test_get_access_tokens_by_user(db: Session) -> None:
    user = create_random_user(db)

    # Create multiple tokens
    for i in range(3):
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        token_create = AccessTokenCreate(name=f"Token {i}", expires_at=expires_at)
        crud.create_access_token(
            session=db, token_create=token_create, owner_id=user.id
        )

    tokens = crud.get_access_tokens_by_user(session=db, user_id=user.id)
    assert len(tokens) == 3

    # Test pagination
    tokens_page = crud.get_access_tokens_by_user(
        session=db, user_id=user.id, skip=1, limit=1
    )
    assert len(tokens_page) == 1


def test_get_access_token_by_id(db: Session) -> None:
    user = create_random_user(db)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    token_create = AccessTokenCreate(name="Test Token", expires_at=expires_at)

    db_token, _ = crud.create_access_token(
        session=db, token_create=token_create, owner_id=user.id
    )

    retrieved_token = crud.get_access_token_by_id(
        session=db, token_id=db_token.id, user_id=user.id
    )
    assert retrieved_token is not None
    assert retrieved_token.id == db_token.id

    # Test with wrong user
    other_user = create_random_user(db)
    retrieved_token = crud.get_access_token_by_id(
        session=db, token_id=db_token.id, user_id=other_user.id
    )
    assert retrieved_token is None


def test_authenticate_with_access_token(db: Session) -> None:
    user = create_random_user(db)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    token_create = AccessTokenCreate(name="Auth Token", expires_at=expires_at)

    db_token, token = crud.create_access_token(
        session=db, token_create=token_create, owner_id=user.id
    )

    # Valid token should authenticate
    authenticated_user = crud.authenticate_with_access_token(session=db, token=token)
    assert authenticated_user is not None
    assert authenticated_user.id == user.id

    # Check that last_used_at was updated
    db.refresh(db_token)
    assert db_token.last_used_at is not None

    # Invalid token should not authenticate
    authenticated_user = crud.authenticate_with_access_token(
        session=db, token="invalid_token"
    )
    assert authenticated_user is None


def test_authenticate_with_expired_token(db: Session) -> None:
    user = create_random_user(db)
    expires_at = datetime.now(timezone.utc) - timedelta(days=1)  # Expired
    token_create = AccessTokenCreate(
        name="Expired Token", expires_at=expires_at
    )

    db_token, token = crud.create_access_token(
        session=db, token_create=token_create, owner_id=user.id
    )

    # Expired token should not authenticate
    authenticated_user = crud.authenticate_with_access_token(session=db, token=token)
    assert authenticated_user is None


def test_authenticate_with_inactive_token(db: Session) -> None:
    user = create_random_user(db)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    token_create = AccessTokenCreate(name="Inactive Token", expires_at=expires_at)

    db_token, token = crud.create_access_token(
        session=db, token_create=token_create, owner_id=user.id
    )

    # Deactivate the token
    db_token.is_active = False
    db.add(db_token)
    db.commit()

    # Inactive token should not authenticate
    authenticated_user = crud.authenticate_with_access_token(session=db, token=token)
    assert authenticated_user is None


def test_revoke_access_token(db: Session) -> None:
    user = create_random_user(db)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    token_create = AccessTokenCreate(name="Revoke Token", expires_at=expires_at)

    db_token, token = crud.create_access_token(
        session=db, token_create=token_create, owner_id=user.id
    )

    # Token should be active initially
    assert db_token.is_active is True

    # Revoke the token
    success = crud.revoke_access_token(
        session=db, token_id=db_token.id, user_id=user.id
    )
    assert success is True

    # Token should now be inactive
    db.refresh(db_token)
    assert db_token.is_active is False

    # Should not be able to authenticate with revoked token
    authenticated_user = crud.authenticate_with_access_token(session=db, token=token)
    assert authenticated_user is None


def test_revoke_nonexistent_token(db: Session) -> None:
    user = create_random_user(db)

    success = crud.revoke_access_token(
        session=db, token_id=uuid.uuid4(), user_id=user.id
    )
    assert success is False


def test_revoke_other_users_token(db: Session) -> None:
    user1 = create_random_user(db)
    user2 = create_random_user(db)

    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    token_create = AccessTokenCreate(name="User1 Token", expires_at=expires_at)
    db_token, _ = crud.create_access_token(
        session=db, token_create=token_create, owner_id=user1.id
    )

    # User2 should not be able to revoke User1's token
    success = crud.revoke_access_token(
        session=db, token_id=db_token.id, user_id=user2.id
    )
    assert success is False

    # Token should still be active
    db.refresh(db_token)
    assert db_token.is_active is True
