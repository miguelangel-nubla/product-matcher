import uuid
from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import AccessTokenCreate, User


def test_create_access_token(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    data = {"name": "Test Token", "expires_at": expires_at.isoformat()}
    r = client.post(
        f"{settings.API_V1_STR}/access-tokens/",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 200
    content = r.json()
    assert "token" in content
    assert "access_token" in content
    assert content["access_token"]["name"] == "Test Token"
    assert content["access_token"]["is_active"] is True
    assert content["access_token"]["expires_at"] is not None


def test_create_access_token_with_expiration(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    data = {
        "name": "Expiring Token",
        "expires_at": expires_at.isoformat(),
    }
    r = client.post(
        f"{settings.API_V1_STR}/access-tokens/",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 200
    content = r.json()
    assert content["access_token"]["expires_at"] is not None


def test_read_access_tokens(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    # Create a token first
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    data = {"name": "List Test Token", "expires_at": expires_at.isoformat()}
    client.post(
        f"{settings.API_V1_STR}/access-tokens/",
        headers=superuser_token_headers,
        json=data,
    )

    # List tokens
    r = client.get(
        f"{settings.API_V1_STR}/access-tokens/",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    content = r.json()
    assert "data" in content
    assert "count" in content
    assert len(content["data"]) >= 1


def test_read_access_token_by_id(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    # Create a token first
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    data = {"name": "Get Test Token", "expires_at": expires_at.isoformat()}
    r = client.post(
        f"{settings.API_V1_STR}/access-tokens/",
        headers=superuser_token_headers,
        json=data,
    )
    token_id = r.json()["access_token"]["id"]

    # Get the token by ID
    r = client.get(
        f"{settings.API_V1_STR}/access-tokens/{token_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    content = r.json()
    assert content["id"] == token_id
    assert content["name"] == "Get Test Token"


def test_revoke_access_token(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    # Create a token first
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    data = {"name": "Revoke Test Token", "expires_at": expires_at.isoformat()}
    r = client.post(
        f"{settings.API_V1_STR}/access-tokens/",
        headers=superuser_token_headers,
        json=data,
    )
    token_id = r.json()["access_token"]["id"]

    # Revoke the token
    r = client.delete(
        f"{settings.API_V1_STR}/access-tokens/{token_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    content = r.json()
    assert content["message"] == "Access token revoked successfully"


def test_authenticate_with_access_token(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    # Create a token first
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    data = {"name": "Auth Test Token", "expires_at": expires_at.isoformat()}
    r = client.post(
        f"{settings.API_V1_STR}/access-tokens/",
        headers=superuser_token_headers,
        json=data,
    )
    access_token = r.json()["token"]

    # Use the access token to authenticate
    headers = {"Authorization": f"Bearer {access_token}"}
    r = client.post(f"{settings.API_V1_STR}/login/test-token", headers=headers)
    assert r.status_code == 200


def test_access_token_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/access-tokens/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


def test_revoke_nonexistent_token(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.delete(
        f"{settings.API_V1_STR}/access-tokens/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


def test_access_tokens_are_user_scoped(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
    db: Session
) -> None:
    # Create token as superuser
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    data = {"name": "Superuser Token", "expires_at": expires_at.isoformat()}
    r = client.post(
        f"{settings.API_V1_STR}/access-tokens/",
        headers=superuser_token_headers,
        json=data,
    )
    superuser_token_id = r.json()["access_token"]["id"]

    # Try to access superuser's token as normal user
    r = client.get(
        f"{settings.API_V1_STR}/access-tokens/{superuser_token_id}",
        headers=normal_user_token_headers,
    )
    assert r.status_code == 404

    # Normal user should only see their own tokens
    r = client.get(
        f"{settings.API_V1_STR}/access-tokens/",
        headers=normal_user_token_headers,
    )
    assert r.status_code == 200
    content = r.json()
    assert content["count"] == 0
