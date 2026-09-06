# events360-backend/app/models/password_reset_token.py
import uuid

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class PasswordResetToken(Base):
    """
    A single-use, expiring password reset link for either an org User or a
    PlatformAdmin — exactly one of the two account FKs is set. Only a SHA-256
    hash of the token is stored; the raw token exists solely inside the
    emailed link, so a database leak can't be used to mint working resets.

    There is deliberately NO self-service "forgot password" flow (no 2FA on
    the platform yet): tokens are issued only by an org owner/admin for
    people in their own org, by any platform admin for org accounts, or by a
    superadmin for platform admin accounts — see the routers.
    """

    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        CheckConstraint(
            "(user_id IS NULL) != (platform_admin_id IS NULL)",
            name="ck_reset_token_exactly_one_account",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    platform_admin_id = Column(
        UUID(as_uuid=True), ForeignKey("platform_admins.id", ondelete="CASCADE"), nullable=True
    )

    token_hash = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)

    # Audit trail: which org admin or platform admin issued the link.
    # SET NULL (not CASCADE) so deleting the issuer keeps the record.
    created_by_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_admin_id = Column(
        UUID(as_uuid=True), ForeignKey("platform_admins.id", ondelete="SET NULL"), nullable=True
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())