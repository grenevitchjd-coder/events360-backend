import uuid
from typing import Optional

from pydantic import BaseModel


class PendingOrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    owner_name: str
    owner_email: str
    status: str
    created_at: str

    class Config:
        from_attributes = True


class ApprovalDecisionRequest(BaseModel):
    notes: Optional[str] = None