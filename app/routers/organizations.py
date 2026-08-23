from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.organization import Organization, OrganizationStatus
from app.models.user import User, UserRole, UserStatus
from app.schemas.organization import OrganizationSignupRequest, OrganizationResponse
from app.services.security import hash_password
from app.services.deps import require_org_owner

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("/signup", response_model=OrganizationResponse, status_code=201)
def signup_organization(payload: OrganizationSignupRequest, db: Session = Depends(get_db)):
    """
    Creates a new Organization (pending_approval) and its owner User in one
    transaction. The owner cannot log in until a platform admin approves
    the organization.
    """
    existing = db.query(User).filter(User.email == payload.owner_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    org = Organization(name=payload.org_name, status=OrganizationStatus.PENDING_APPROVAL)
    db.add(org)
    db.flush()  # get org.id without committing yet

    owner = User(
        organization_id=org.id,
        name=payload.owner_name,
        email=payload.owner_email,
        password_hash=hash_password(payload.owner_password),
        role=UserRole.ORG_OWNER,
        status=UserStatus.ACTIVE,
    )
    db.add(owner)
    db.commit()
    db.refresh(org)

    return org


@router.delete("/{org_id}", status_code=204)
def delete_own_organization(
    org_id: str,
    db: Session = Depends(get_db),
    owner: User = Depends(require_org_owner),
):
    """
    Self-service deletion: the org owner can delete their own organization
    at any time. Cascades to every related record (users, events, roles,
    staff assignments) via ON DELETE CASCADE at the database level.
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")
    db.delete(org)
    db.commit()