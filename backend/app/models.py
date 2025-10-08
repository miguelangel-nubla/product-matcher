import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, EmailStr
from sqlmodel import Field, Relationship, SQLModel


class GlobalSettings(SQLModel):
    default_threshold: float
    max_candidates: int


class BackendInfo(SQLModel):
    name: str
    description: str


class AdapterConfig(SQLModel):
    """Adapter-specific configuration."""

    type: str
    config: dict[str, Any] = Field(default_factory=dict)


class BackendConfig(SQLModel):
    """Complete backend configuration with type safety."""

    description: str
    language: str
    adapter: AdapterConfig


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=40)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=40)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    match_logs: list["MatchLog"] = Relationship(cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Model for pending queries that need manual resolution
class PendingQuery(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    original_text: str = Field(min_length=1, max_length=255)
    normalized_text: str = Field(min_length=1, max_length=255)
    candidates: str | None = Field(default=None)  # JSON string of candidates array
    status: str = Field(default="pending", max_length=20)  # pending, resolved, ignored
    backend: str = Field(min_length=1, max_length=50)  # Backend instance name
    threshold: float = Field(ge=0.0, le=1.0)  # Threshold that was used for matching
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship()


# Model for logging successful matches for analytics and learning
class MatchLog(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    original_text: str = Field(min_length=1, max_length=255)
    normalized_text: str = Field(min_length=1, max_length=255)
    backend: str = Field(min_length=1, max_length=50)  # Backend instance name
    matched_product_id: str = Field(min_length=1, max_length=255)  # External product ID
    matched_text: str = Field(
        min_length=1, max_length=255
    )  # The alias that was matched
    confidence_score: float = Field(ge=0.0, le=1.0)
    threshold_used: float = Field(ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship()


class PendingQueryPublic(SQLModel):
    id: uuid.UUID
    original_text: str
    normalized_text: str
    candidates: str | None
    status: str
    backend: str
    threshold: float
    created_at: datetime
    owner_id: uuid.UUID


class PendingQueriesPublic(SQLModel):
    data: list[PendingQueryPublic]
    count: int


class MatchLogPublic(SQLModel):
    id: uuid.UUID
    original_text: str
    normalized_text: str
    backend: str
    matched_product_id: str
    matched_text: str
    confidence_score: float
    threshold_used: float
    created_at: datetime
    owner_id: uuid.UUID


class MatchLogsPublic(SQLModel):
    data: list[MatchLogPublic]
    count: int


# Models for matching API
class MatchRequest(SQLModel):
    text: str = Field(min_length=1, max_length=255)
    threshold: float | None = Field(
        default=None, ge=0.0, le=1.0
    )  # None means use global default
    backend: str = Field(
        min_length=1, max_length=50
    )  # Backend instance name (backend1, backend2, etc.)
    create_pending: bool = Field(
        default=True
    )  # Whether to create pending items for unmatched queries


class MatchCandidate(SQLModel):
    product_id: str
    confidence: float


class DebugStep(BaseModel):
    message: str
    timestamp: float
    data: Any = None


class MatchResult(SQLModel):
    success: bool  # True if match exceeded threshold
    normalized_input: str
    pending_query_id: uuid.UUID | None = None
    candidates: list[MatchCandidate] = []  # Top 5 best matches found
    debug_info: list[
        DebugStep
    ] | None = None  # Debug information as list of step objects


# Model for resolving pending queries
class ResolveRequest(SQLModel):
    pending_query_id: uuid.UUID
    action: str = Field(regex="^(assign|ignore)$")
    product_id: str | None = (
        None  # External product ID (required if action is "assign")
    )
    custom_alias: str | None = None  # Optional custom alias text


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)
