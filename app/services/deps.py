from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserStatus
from app.models.organization import Organization, OrganizationStatus
from app.models.platform_admin import PlatformAdmin, PlatformAdminStatus
from app.services.security import decode_access_token

# Two separate token URLs so Swagger UI (/docs) shows distinct login forms
# for org users vs. platform admins.
user_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
admin_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/login", auto_error=False)
downstream_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/oauth/token", auto_error=False)


def get_current_user(
    token: str = Depends(user_oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials"
    )
    if not token:
        raise credentials_error
    try:
        payload = decode_access_token(token)
        if payload.get("type") != "user":
            raise credentials_error
        user_id = payload.get("sub")
    except JWTError:
        raise credentials_error

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_error
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="This account has been deactivated.")

    org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    if org is None or org.status not in (OrganizationStatus.ACTIVE,):
        raise HTTPException(
            status_code=403,
            detail="Your organization is not active. Contact support.",
        )
    return user


def get_current_platform_admin(
    token: str = Depends(admin_oauth2_scheme), db: Session = Depends(get_db)
) -> PlatformAdmin:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials"
    )
    if not token:
        raise credentials_error
    try:
        payload = decode_access_token(token)
        if payload.get("type") != "platform_admin":
            raise credentials_error
        admin_id = payload.get("sub")
    except JWTError:
        raise credentials_error

    admin = db.query(PlatformAdmin).filter(PlatformAdmin.id == admin_id).first()
    if admin is None or admin.status != PlatformAdminStatus.ACTIVE:
        raise credentials_error
    return admin


def require_superadmin(admin: PlatformAdmin = Depends(get_current_platform_admin)) -> PlatformAdmin:
    """Use this for endpoints only a superadmin (not support_admin) can hit,
    e.g. creating other PlatformAdmin accounts."""
    if admin.role.value != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin access required.")
    return admin


def require_org_admin(org_id: str, user: User = Depends(get_current_user)) -> User:
    """
    Use for endpoints that manage an org's roles, events, or staff.
    Enforces two things: the user must be org_owner or org_admin (not staff),
    AND the org_id in the URL must match the user's own organization —
    this is the multi-tenant isolation check that stops one org's admin
    from managing a different org's data.
    """
    if str(user.organization_id) != org_id:
        raise HTTPException(status_code=403, detail="You do not have access to this organization.")
    if user.role.value not in ("org_owner", "org_admin"):
        raise HTTPException(status_code=403, detail="Org admin access required.")
    return user


def require_org_owner(org_id: str, user: User = Depends(get_current_user)) -> User:
    """
    Stricter than require_org_admin — for destructive, irreversible actions
    like deleting the organization itself. org_admin is deliberately NOT
    enough here; only the org_owner can do this.
    """
    if str(user.organization_id) != org_id:
        raise HTTPException(status_code=403, detail="You do not have access to this organization.")
    if user.role.value != "org_owner":
        raise HTTPException(status_code=403, detail="Only the organization owner can do this.")
    return user


def get_current_oauth_user(
    token: str = Depends(downstream_oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """
    Validates a token issued to a downstream app (EventNXT, etc.) via the
    OAuth2 flow — distinct from get_current_user, which validates a token
    issued directly to a user logging into Events360 itself. Used by
    /oauth/userinfo, which downstream apps call to verify a token and get
    the identity behind it (token introspection pattern — no shared secret
    between services, downstream apps never decode the JWT themselves).
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials"
    )
    if not token:
        raise credentials_error
    try:
        payload = decode_access_token(token)
        if payload.get("type") != "oauth_access":
            raise credentials_error
        user_id = payload.get("sub")
    except JWTError:
        raise credentials_error

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or user.status != UserStatus.ACTIVE:
        raise credentials_error
    return user