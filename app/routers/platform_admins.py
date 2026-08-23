from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.platform_admin import PlatformAdmin, PlatformAdminRole, PlatformAdminStatus
from app.schemas.platform_admin import PlatformAdminCreateRequest, PlatformAdminResponse
from app.services.security import hash_password
from app.services.deps import require_superadmin, get_current_platform_admin

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