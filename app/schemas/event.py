import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EventCreateRequest(BaseModel):
    name: str
    event_date: Optional[datetime] = None


class EventResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    event_date: Optional[datetime] = None

    class Config:
        from_attributes = True