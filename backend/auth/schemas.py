import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.tenant import TenantStatus
from models.user import UserRole


class TenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    status: TenantStatus
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=12, max_length=128)
    role: UserRole = UserRole.VIEWER

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not any(character.isdigit() for character in value):
            raise ValueError("Password must contain at least one number")
        if not any(character.isalpha() for character in value):
            raise ValueError("Password must contain at least one letter")
        return value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class CurrentUser(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    full_name: str
    role: UserRole


class BootstrapRequest(BaseModel):
    tenant: TenantCreate
    user: UserCreate


class BootstrapResponse(BaseModel):
    tenant: TenantRead
    user: UserRead
