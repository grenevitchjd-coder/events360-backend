import uuid

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Permission(Base):
    """
    Fixed catalog defined by the platform, not user-created. Orgs combine
    these into custom Roles rather than inventing new permissions.
    Populated via seed script — see app/seeds/seed_permissions.py.
    """

    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String, unique=True, nullable=False, index=True)  # e.g. "manage_events"
    description = Column(String, nullable=False)