# events360-backend/app/routers/org_users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole, UserStatus
from app.models.staff_assignment import StaffAssignment
from app.schemas.user import OrgUserCreateRequest, OrgUserResponse
from app.schemas.auth import MessageResponse
from app.services.security import hash_password
from app.services.permissions import require_org_permission
from app.services.password_reset import issue_and_email_reset_link, issue_and_email_invite_link
from app.models.organization import Organization
import secrets

router = APIRouter(prefix="/organizations/{org_id}/users", tags=["org-users"])


@router.post("", response_model=OrgUserResponse, status_code=201)
def create_org_user(
    org_id: str,
    payload: OrgUserCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_org_permission("events360.staff.manage")),
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

    # The account starts with an unusable random password; the invite email's
    # set-password link is the only way a real one gets created.
    new_user = User(
        organization_id=org_id,
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(secrets.token_urlsafe(32)),
        role=UserRole(payload.role),
        status=UserStatus.ACTIVE,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    org = db.query(Organization).filter(Organization.id == org_id).first()
    try:
        issue_and_email_invite_link(
            db,
            user=new_user,
            org_name=org.name if org else "your organization",
            initiated_by=admin.name,
            created_by_user_id=admin.id,
        )
    except HTTPException:
        # No invite = no way to ever log in. Undo the creation entirely so a
        # failed email never strands an unreachable account (token rows
        # cascade with the user), and tell the organizer nothing was made.
        db.delete(new_user)
        db.commit()
        raise HTTPException(
            status_code=502,
            detail="The invite email could not be sent, so the person was NOT added. Check the server's email settings and try again.",
        )
    return new_user


@router.get("", response_model=list[OrgUserResponse])
def list_org_users(
    org_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_org_permission("events360.staff.view")),
):
    return db.query(User).filter(User.organization_id == org_id).all()


@router.post("/{user_id}/reactivate", response_model=OrgUserResponse)
def reactivate_org_user(
    org_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_org_permission("events360.staff.manage")),
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
    admin: User = Depends(require_org_permission("events360.staff.manage")),
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
        initiated_by=f"{admin.name} (from your organization)",
        created_by_user_id=admin.id,
    )
    return MessageResponse(detail=detail)

def _guard_target(admin: User, target: User, action: str) -> None:
    """Shared rules for deactivate/delete: never yourself (no self-lockout),
    never the org owner (the account that anchors the org), and acting on
    another org_admin takes the owner — mirroring who can CREATE admins."""
    if str(target.id) == str(admin.id):
        raise HTTPException(status_code=400, detail=f"You cannot {action} your own account.")
    if target.role == UserRole.ORG_OWNER:
        raise HTTPException(status_code=400, detail=f"The organization owner cannot be {action}d.")
    if target.role == UserRole.ORG_ADMIN and admin.role.value != "org_owner":
        raise HTTPException(
            status_code=403,
            detail=f"Only the organization owner can {action} another admin.",
        )


@router.post("/{user_id}/deactivate", response_model=OrgUserResponse)
def deactivate_org_user(
    org_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_org_permission("events360.staff.manage")),
):
    """
    Manually deactivate an account — login is blocked until someone
    reactivates it. Role assignments and history stay intact, so this is
    the right tool for "left for the season" or "pause access now".
    """
    target = db.query(User).filter(User.id == user_id, User.organization_id == org_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found in this organization.")
    _guard_target(admin, target, "deactivate")

    target.status = UserStatus.INACTIVE
    db.commit()
    db.refresh(target)
    return target


@router.delete("/{user_id}", status_code=204)
def delete_org_user(
    org_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_org_permission("events360.staff.manage")),
):
    """
    Permanently remove a person from the org. Their role assignments go
    with them (explicitly, below — no dangling grants); anything they
    created stays. For a temporary pause, use deactivate instead.
    """
    target = db.query(User).filter(User.id == user_id, User.organization_id == org_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found in this organization.")
    _guard_target(admin, target, "delete")

    db.query(StaffAssignment).filter(StaffAssignment.user_id == target.id).delete(
        synchronize_session=False
    )
    db.delete(target)
    db.commit()