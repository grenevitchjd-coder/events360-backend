import uuid

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class ProductEntitlement(Base):
    """
    Master switch: does this org have access to a given product
    (product_key matches an OAuthClient.client_id — "eventnxt", later
    "castnxt"/"planxt")? Absence of a row means ENABLED by default — a row
    only needs to exist to explicitly turn a product OFF for an org, so
    nothing breaks for orgs already using a product when this ships.
    Enforced centrally at /oauth/authorize, not duplicated per product app.
    """

    __tablename__ = "product_entitlements"
    __table_args__ = (UniqueConstraint("organization_id", "product_key", name="uq_org_product"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    product_key = Column(String, nullable=False)  # e.g. "eventnxt"
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())