import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator


class EventCreateRequest(BaseModel):
    name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None  # supports multi-day events

    @model_validator(mode="after")
    def check_end_after_start(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date.")
        return self


class EventResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: str
    retention_days: int
    retention_reminder_sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EventRetentionUpdateRequest(BaseModel):
    retention_days: int

    @field_validator("retention_days")
    @classmethod
    def check_retention_range(cls, v: int) -> int:
        # Default is 30, cap is 90 (3 months), per architecture doc
        if v < 1 or v > 90:
            raise ValueError("retention_days must be between 1 and 90.")
        return v