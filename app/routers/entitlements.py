from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.oauth_client import OAuthClient
from app.schemas.entitlement import ProductEntitlementResponse
from app.services.deps import get_current_user
from app.services.entitlements import is_org_entitled, KNOWN_PRODUCTS

router = APIRouter(tags=["entitlements"])


@router.get("/entitlements", response_model=list[ProductEntitlementResponse])
def list_my_entitlements(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    What this org can launch — powers the "Launch EventNXT" (etc.) buttons
    on the org dashboard. org_id comes from the token itself, not a path
    param, so there's no possibility of asking about a different org's
    entitlements by mistake.
    """
    clients = db.query(OAuthClient).filter(OAuthClient.client_id.in_(KNOWN_PRODUCTS)).all()
    results = []
    for client in clients:
        enabled = is_org_entitled(db, user.organization_id, client.client_id)
        results.append(
            ProductEntitlementResponse(
                product_key=client.client_id,
                name=client.name,
                enabled=enabled,
                launch_url=client.launch_url if enabled else None,
            )
        )
    return results