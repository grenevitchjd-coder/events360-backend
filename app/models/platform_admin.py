import enum
import uuid

from sqlalchemy import Column, String, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class PlatformAdminRole(str, enum.Enum):
    SUPERADMIN = "superadmin"  # can also create/promote other PlatformAdmin accounts
    SUPPORT_ADMIN = "support_admin"  # full operational access, cannot create new admins


class PlatformAdminStatus(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class PlatformAdmin(Base):
    """
    Platform-level staff (e.g. Tito), entirely separate from Organization-scoped
    Users. Not tied to any Organization. Bootstrapped via seed script since
    there's no existing admin to approve the first account.
    """

    __tablename__ = "platform_admins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)

    role = Column(
        SAEnum(
            PlatformAdminRole,
            name="platform_admin_role",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
    )
    status = Column(
        SAEnum(
            PlatformAdminStatus,
            name="platform_admin_status",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=PlatformAdminStatus.ACTIVE,
    )

    # Audit trail: which admin created this account (null for the first seeded superadmin)
    created_by = Column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())