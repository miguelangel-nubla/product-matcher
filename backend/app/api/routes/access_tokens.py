import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app import crud
from app.api.deps import CurrentUserJwtOnly, SessionDep
from app.models import (
    AccessTokenCreate,
    AccessTokenCreated,
    AccessTokenPublic,
    AccessTokensPublic,
    Message,
)

router = APIRouter()


@router.post("/", response_model=AccessTokenCreated)
def create_access_token(
    *,
    session: SessionDep,
    current_user: CurrentUserJwtOnly,
    token_in: AccessTokenCreate,
) -> Any:
    """
    Create a new access token.
    """
    db_token, token = crud.create_access_token(
        session=session, token_create=token_in, owner_id=current_user.id
    )
    return AccessTokenCreated(
        token=token, access_token=AccessTokenPublic.model_validate(db_token)
    )


@router.get("/", response_model=AccessTokensPublic)
def read_access_tokens(
    session: SessionDep,
    current_user: CurrentUserJwtOnly,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve access tokens for the current user.
    """
    tokens = crud.get_access_tokens_by_user(
        session=session, user_id=current_user.id, skip=skip, limit=limit
    )
    return AccessTokensPublic(data=tokens, count=len(tokens))


@router.get("/{token_id}", response_model=AccessTokenPublic)
def read_access_token(
    *, session: SessionDep, current_user: CurrentUserJwtOnly, token_id: uuid.UUID
) -> Any:
    """
    Get access token by ID.
    """
    token = crud.get_access_token_by_id(
        session=session, token_id=token_id, user_id=current_user.id
    )
    if not token:
        raise HTTPException(status_code=404, detail="Access token not found")
    return token


@router.delete("/{token_id}", response_model=Message)
def revoke_access_token(
    *, session: SessionDep, current_user: CurrentUserJwtOnly, token_id: uuid.UUID
) -> Any:
    """
    Revoke an access token.
    """
    success = crud.revoke_access_token(
        session=session, token_id=token_id, user_id=current_user.id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Access token not found")
    return Message(message="Access token revoked successfully")
