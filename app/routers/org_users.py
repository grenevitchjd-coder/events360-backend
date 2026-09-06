# events360-backend/app/routers/org_users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole, UserStatus
from app.schemas.user import OrgUserCreateRequest, OrgUserResponse
from app.schemas.auth import MessageResponse
from app.services.security import hash_password
from app.services.deps import require_org_admin
from app.services.password_reset import issue_and_email_reset_link

router = APIRouter(prefix="/organizations/{org_id}/users", tags=["org-users"])


@router.post("", response_model=OrgUserResponse, status_code=201)
def create_org_user(
    org_id: str,
    payload: OrgUserCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_org_admin),
):
    """
    Adds a new person to the org. Creating an org_admin (not just staff) is
    restricted to the org_owner — mirrors how only superadmins can create
    other PlatformAdmin accounts on the platform side.
    """
    if payload.role == "org_admin" and admin.role.value != "org_owner":
        raise HTTPException(status_code=403, detail="Only the organization owner can add other admins.")

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="A user with this email already exists.")

    new_user = User(
        organization_id=org_id,
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole(payload.role),
        status=UserStatus.ACTIVE,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.get("", response_model=list[OrgUserResponse])
def list_org_users(
    org_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_org_admin),
):
    return db.query(User).filter(User.organization_id == org_id).all()


@router.post("/{user_id}/reactivate", response_model=OrgUserResponse)
def reactivate_org_user(
    org_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_org_admin),
):
    """
    Manual reactivation after the 30-day inactivity job deactivates a staff
    account — promised in the architecture doc, previously unbuilt.
    """
    target = db.query(User).filter(User.id == user_id, User.organization_id == org_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found in this organization.")
    target.status = UserStatus.ACTIVE
    db.commit()
    db.refresh(target)
    return target

@router.post("/{user_id}/send-password-reset", response_model=MessageResponse)
def send_org_user_password_reset(
    org_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_org_admin),
):
    """
    Emails the person a single-use password reset link. There is deliberately
    no self-service "forgot password" endpoint — with no 2FA on the platform,
    resets happen only when an org owner/admin (here) or a platform admin
    initiates one for a person they already know. The link goes to the
    account's own email; the initiator never sees or sets the new password.
    """
    target = db.query(User).filter(User.id == user_id, User.organization_id == org_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found in this organization.")

    detail = issue_and_email_reset_link(
        db,
        user=target,
        initiated_by=f"{admin.name} (an admin of your organization)",
        created_by_user_id=admin.id,
    )
    return MessageResponse(detail=detail)