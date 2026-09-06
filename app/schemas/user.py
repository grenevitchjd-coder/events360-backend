import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.services.security import validate_password_policy


class OrgUserCreateRequest(BaseModel):
    # No password field: the person sets their own via the emailed invite
    # link — organizers never type or know anyone's password.
    name: str
    email: EmailStr
    role: Literal["org_admin", "staff"]  # org_owner is set only at signup, never here

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