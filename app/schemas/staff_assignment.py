import uuid
from typing import Optional

from pydantic import BaseModel


class StaffAssignmentCreateRequest(BaseModel):
    user_id: uuid.UUID
    role_id: uuid.UUID
    event_id: Optional[uuid.UUID] = None  # omit/null = org-wide scope


class StaffAssignmentResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    role_id: uuid.UUID
    event_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True