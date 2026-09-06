# events360-backend/app/schemas/admin.py
import uuid
from datetime import datetime
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


class AdminEventRow(BaseModel):
    """One event with its org attached — powers the admin Events tab
    (all events across the platform, grouped by organization client-side)."""

    id: uuid.UUID
    organization_id: uuid.UUID
    organization_name: str
    name: str
    status: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    retention_days: int


class AdminOrgAdminRow(BaseModel):
    """One org owner/admin with their org attached — powers the admin People
    tab (reset links go only to owners and org admins; staff lockouts are
    handled by their own org's admins, per the platform's security posture)."""

    id: uuid.UUID
    organization_id: uuid.UUID
    organization_name: str
    name: str
    email: str
    role: str
    status: str