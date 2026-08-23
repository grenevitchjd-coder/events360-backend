import uuid
from typing import List

from pydantic import BaseModel


class PermissionResponse(BaseModel):
    id: uuid.UUID
    key: str
    description: str

    class Config:
        from_attributes = True


class RoleCreateRequest(BaseModel):
    name: str
    permission_keys: List[str]  # e.g. ["manage_guests", "view_reports"]


class RoleResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    permissions: List[PermissionResponse]

    class Config:
        from_attributes = True