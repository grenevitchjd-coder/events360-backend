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