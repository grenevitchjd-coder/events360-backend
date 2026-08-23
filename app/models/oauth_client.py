import uuid

from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class OAuthClient(Base):
    """
    A downstream product app (EventNXT, later CastNXT/PlaNXT) registered
    to authenticate org users via "Sign in with Events360". client_secret
    is hashed the same way passwords are — never stored in plaintext.
    """

    __tablename__ = "oauth_clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(String, unique=True, nullable=False, index=True)  # e.g. "eventnxt"
    client_secret_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)  # e.g. "EventNXT"
    # Comma-separated list of allowed redirect URIs — the authorize/token
    # endpoints reject any redirect_uri not in this list.
    redirect_uris = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())