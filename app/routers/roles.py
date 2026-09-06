# events360-backend/app/routers/roles.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.role import Role
from app.models.permission import Permission
from app.models.staff_assignment import StaffAssignment
from app.models.user import User
from app.schemas.role import RoleCreateRequest, RoleUpdateRequest, RoleResponse, PermissionResponse
from app.services.deps import require_org_admin, get_current_user

router = APIRouter(tags=["roles"])


@router.get("/permissions", response_model=list[PermissionResponse])
def list_permission_catalog(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),  # any logged-in org user can see the catalog
):
    """The fixed, platform-defined list orgs pick from when building a Role.
    Ordered so the Roles UI renders deterministically."""
    return db.query(Permission).order_by(Permission.category, Permission.key).all()


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

@router.put("/organizations/{org_id}/roles/{role_id}", response_model=RoleResponse)
def update_role(
    org_id: str,
    role_id: str,
    payload: RoleUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_org_admin),
):
    """
    Edit a role's name and permission set (the list REPLACES the current
    set). Everyone assigned this role gets the new grants immediately —
    that's the point of roles: fix it once, it applies everywhere.
    """
    role = db.query(Role).filter(Role.id == role_id, Role.organization_id == org_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found.")

    permissions = db.query(Permission).filter(Permission.key.in_(payload.permission_keys)).all()
    found_keys = {p.key for p in permissions}
    missing = set(payload.permission_keys) - found_keys
    if missing:
        raise HTTPException(status_code=400, detail=f"Unknown permission key(s): {', '.join(missing)}")

    role.name = payload.name
    role.permissions = permissions
    db.commit()
    db.refresh(role)
    return role


@router.delete("/organizations/{org_id}/roles/{role_id}", status_code=204)
def delete_role(
    org_id: str,
    role_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_org_admin),
):
    """
    Deleting a role is refused while staff hold it — silently stripping
    people's access via a cascade would be a surprise; removing the
    assignments first is a deliberate act on the Staff tab.
    """
    role = db.query(Role).filter(Role.id == role_id, Role.organization_id == org_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found.")

    assigned = db.query(StaffAssignment).filter(StaffAssignment.role_id == role.id).count()
    if assigned:
        raise HTTPException(
            status_code=400,
            detail=(
                f"This role is assigned to {assigned} staff member(s). "
                "Remove those assignments on the Staff tab first."
            ),
        )

    db.delete(role)
    db.commit()