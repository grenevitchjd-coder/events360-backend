# events360-backend/app/schemas/auth.py
from typing import Literal

from pydantic import BaseModel, field_validator

from app.services.security import validate_password_policy


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    detail: str


class PasswordResetRequest(BaseModel):
    token: str
    new_password: str

    # Same server-side policy as signup — a reset can't set a weaker password.
    @field_validator("new_password")
    @classmethod
    def check_password_policy(cls, v: str) -> str:
        validate_password_policy(v)
        return v


class PasswordResetCompleteResponse(BaseModel):
    # Tells the reset page which login to link back to.
    account_type: Literal["org_user", "platform_admin"]
    detail: str