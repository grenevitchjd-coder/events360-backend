from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.organization import Organization, OrganizationStatus
from app.models.user import User, UserRole, UserStatus
from app.schemas.organization import OrganizationSignupRequest, OrganizationResponse
from app.services.security import hash_password

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