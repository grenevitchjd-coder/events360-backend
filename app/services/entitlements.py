from sqlalchemy.orm import Session

from app.models.product_entitlement import ProductEntitlement

# The known products, for computing a full picture even when no row exists
# yet for a given org. New products get added here as they're built.
KNOWN_PRODUCTS = ["eventnxt"]


def is_org_entitled(db: Session, organization_id, product_key: str) -> bool:
    """
    Default-enabled: absence of a row means the org has access. A row only
    needs to exist to explicitly disable a product for an org — this means
    shipping this feature doesn't silently cut off any org already using a
    product that predates entitlements existing at all.
    """
    row = (
        db.query(ProductEntitlement)
        .filter(
            ProductEntitlement.organization_id == organization_id,
            ProductEntitlement.product_key == product_key,
        )
        .first()
    )
    if row is None:
        return True
    return row.enabled