import uuid

from pydantic import BaseModel, EmailStr, field_validator

from app.services.security import validate_password_policy


class OrganizationSignupRequest(BaseModel):
    org_name: str
    owner_name: str
    owner_email: EmailStr
    owner_password: str

    @field_validator("owner_password")
    @classmethod
    def check_password_policy(cls, v: str) -> str:
        validate_password_policy(v)  # raises ValueError -> FastAPI turns into 422
        return v


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: str

    class Config:
        from_attributes = True