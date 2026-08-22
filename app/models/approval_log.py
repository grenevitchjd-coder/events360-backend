import enum
import uuid

from sqlalchemy import Column, String, DateTime, Enum as SAEnum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class ApprovalDecision(str, enum.Enum):
    APPROVED = "approved"
    DENIED = "denied"


class OrganizationApprovalLog(Base):
    """
    Audit trail for org signup approval decisions. Stores org_name/org_email
    as a snapshot (not just a FK) so the record survives even if the
    organization is later deleted.
    """

    __tablename__ = "organization_approval_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=True)  # nullable: org may later be deleted
    organization_name_snapshot = Column(String, nullable=False)

    decision = Column(SAEnum(ApprovalDecision, name="approval_decision"), nullable=False)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=False)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())