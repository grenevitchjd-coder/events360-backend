import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.services.security import validate_password_policy


class OrgUserCreateRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Literal["org_admin", "staff"]  # org_owner is set only at signup, never here

    @field_validator("password")
    @classmethod
    def check_password_policy(cls, v: str) -> str:
        validate_password_policy(v)
        return v


class OrgUserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: str
    status: str
    last_active_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True