# events360-backend/app/routers/platform_admins.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.platform_admin import PlatformAdmin, PlatformAdminRole, PlatformAdminStatus
from app.schemas.platform_admin import PlatformAdminCreateRequest, PlatformAdminResponse
from app.schemas.auth import MessageResponse
from app.services.security import hash_password
from app.services.deps import require_superadmin, get_current_platform_admin
from app.services.password_reset import issue_and_email_reset_link

router = APIRouter(prefix="/admin/platform-admins", tags=["platform-admins"])


@router.post("", response_model=PlatformAdminResponse, status_code=201)
def create_platform_admin(
    payload: PlatformAdminCreateRequest,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(require_superadmin),
):
    """
    Only superadmins can create new PlatformAdmin accounts (of either role).
    support_admin accounts cannot reach this endpoint at all.
    """
    existing = db.query(PlatformAdmin).filter(PlatformAdmin.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="A platform admin with this email already exists.")

    new_admin = PlatformAdmin(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=PlatformAdminRole(payload.role),
        status=PlatformAdminStatus.ACTIVE,
        created_by=admin.id,
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return new_admin


@router.get("", response_model=list[PlatformAdminResponse])
def list_platform_admins(
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),  # any active platform admin can view
):
    return db.query(PlatformAdmin).all()


@router.post("/{admin_id}/disable", response_model=PlatformAdminResponse)
def disable_platform_admin(
    admin_id: str,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(require_superadmin),
):
    if admin_id == str(admin.id):
        raise HTTPException(status_code=400, detail="You cannot disable your own account.")

    target = db.query(PlatformAdmin).filter(PlatformAdmin.id == admin_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Platform admin not found.")

    target.status = PlatformAdminStatus.DISABLED
    db.commit()
    db.refresh(target)
    return target


@router.post("/{admin_id}/enable", response_model=PlatformAdminResponse)
def enable_platform_admin(
    admin_id: str,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(require_superadmin),
):
    target = db.query(PlatformAdmin).filter(PlatformAdmin.id == admin_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Platform admin not found.")

    target.status = PlatformAdminStatus.ACTIVE
    db.commit()
    db.refresh(target)
    return target

@router.post("/{admin_id}/send-password-reset", response_model=MessageResponse)
def send_platform_admin_password_reset(
    admin_id: str,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(require_superadmin),
):
    """
    Emails a platform admin a single-use password reset link. Restricted to
    superadmins — matching the create/disable pattern for admin accounts.
    Sending to yourself is allowed (it's just a password change with extra
    steps). The link goes to the target's own email.
    """
    target = db.query(PlatformAdmin).filter(PlatformAdmin.id == admin_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Platform admin not found.")

    detail = issue_and_email_reset_link(
        db,
        platform_admin=target,
        initiated_by=f"{admin.name} (superadmin)",
        created_by_admin_id=admin.id,
    )
    return MessageResponse(detail=detail)