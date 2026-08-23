import enum
import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class EventStatus(str, enum.Enum):
    ACTIVE = "active"
    LOCKED = "locked"  # superadmin support action — no self-service unlock (org admins can't set this)


class Event(Base):
    """
    Minimal for now — just enough for StaffAssignment to scope against, plus
    post-event data retention fields. Full fields (product tags, approval
    status inheritance, etc.) are filled in as later slices need them.
    """

    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    event_date = Column(DateTime(timezone=True), nullable=True)

    status = Column(
        SAEnum(EventStatus, name="event_status", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
        default=EventStatus.ACTIVE,
    )

    # Post-event data retention (architecture doc): default 30 days, capped at
    # 90 (enforced in the API schema, not the DB, so it stays adjustable).
    retention_days = Column(Integer, nullable=False, default=30)
    # Set once the 14-day-before reminder email has gone out, so the job
    # doesn't send it twice.
    retention_reminder_sent_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())