import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.services.security import validate_password_policy


class PlatformAdminCreateRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Literal["superadmin", "support_admin"]

    @field_validator("password")
    @classmethod
    def check_password_policy(cls, v: str) -> str:
        validate_password_policy(v)
        return v


class PlatformAdminResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: str
    status: str
    created_by: Optional[uuid.UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True