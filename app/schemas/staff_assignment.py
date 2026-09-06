import uuid
from typing import Optional

from pydantic import BaseModel


class StaffAssignmentCreateRequest(BaseModel):
    user_id: uuid.UUID
    role_id: uuid.UUID
    event_id: Optional[uuid.UUID] = None  # omit/null = org-wide scope


class StaffAssignmentUpdateRequest(BaseModel):
    # Both optional — send only what changes. event_id explicitly null
    # means "make it org-wide", so we track whether it was provided.
    role_id: str | None = None
    event_id: str | None = None


class StaffAssignmentResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    role_id: uuid.UUID
    event_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True