import uuid

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class OAuthAuthorizationCode(Base):
    """
    Short-lived (10 min), single-use code issued after a user approves an
    OAuth authorize request. Exchanged once for an access token, then
    marked used — reusing a code, or presenting an expired one, is rejected.
    """

    __tablename__ = "oauth_authorization_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String, unique=True, nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("oauth_clients.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    redirect_uri = Column(String, nullable=False)  # must match exactly at token exchange
    scope = Column(String, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())