from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserStatus
from app.models.organization import Organization, OrganizationStatus
from app.schemas.auth import TokenResponse
from app.services.security import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Org user login. `form_data.username` is the user's email (OAuth2 password
    flow convention). Blocks login if the org isn't active yet (still
    pending_approval, denied, or locked) or the user account is deactivated.
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=403,
            detail="This account has been deactivated due to inactivity. Contact your org admin.",
        )

    org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    if org.status == OrganizationStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=403,
            detail="Your organization is still awaiting approval.",
        )
    if org.status == OrganizationStatus.DENIED:
        raise HTTPException(status_code=403, detail="Your organization's signup was not approved.")
    if org.status == OrganizationStatus.LOCKED:
        raise HTTPException(
            status_code=403,
            detail="Your organization's account is locked, likely due to a lapsed subscription.",
        )

    # Track activity for the 30-day inactivity auto-deactivation job
    user.last_active_at = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(
        subject=str(user.id),
        extra_claims={"type": "user", "org_id": str(user.organization_id), "role": user.role.value},
    )
    return TokenResponse(access_token=token)