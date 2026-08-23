from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.role import Role
from app.models.permission import Permission
from app.models.user import User
from app.schemas.role import RoleCreateRequest, RoleResponse, PermissionResponse
from app.services.deps import require_org_admin, get_current_user

router = APIRouter(tags=["roles"])


@router.get("/permissions", response_model=list[PermissionResponse])
def list_permission_catalog(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),  # any logged-in org user can see the catalog
):
    """The fixed, platform-defined list orgs pick from when building a Role."""
    return db.query(Permission).all()


@router.post("/organizations/{org_id}/roles", response_model=RoleResponse, status_code=201)
def create_role(
    org_id: str,
    payload: RoleCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_org_admin),
):
    permissions = db.query(Permission).filter(Permission.key.in_(payload.permission_keys)).all()
    found_keys = {p.key for p in permissions}
    missing = set(payload.permission_keys) - found_keys
    if missing:
        raise HTTPException(status_code=400, detail=f"Unknown permission key(s): {', '.join(missing)}")

    role = Role(organization_id=org_id, name=payload.name, permissions=permissions)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.get("/organizations/{org_id}/roles", response_model=list[RoleResponse])
def list_roles(
    org_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_org_admin),
):
    return db.query(Role).filter(Role.organization_id == org_id).all()