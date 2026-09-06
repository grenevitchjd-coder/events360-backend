# events360-backend/app/routers/auth.py
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserStatus
from app.models.organization import Organization, OrganizationStatus
from app.models.platform_admin import PlatformAdmin
from app.models.password_reset_token import PasswordResetToken
from app.schemas.auth import TokenResponse, PasswordResetRequest, PasswordResetCompleteResponse
from app.services.security import verify_password, create_access_token, hash_password
from app.services.password_reset import hash_token
from app.services.deps import get_current_user
from app.services.permissions import effective_permissions

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
            detail="This account has been deactivated. Contact your org admin.",
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


@router.post("/reset-password", response_model=PasswordResetCompleteResponse)
def reset_password(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    """
    Public endpoint that finishes a password reset. The link that carries the
    token can only have been issued by an org owner/admin or a platform admin
    (there is deliberately no self-service request flow), and was emailed to
    the account's own address. Tokens are single-use, expire in 60 minutes,
    and the new password goes through the same server-side policy as signup.
    Works for both org Users and PlatformAdmins — the response says which,
    so the frontend can link back to the right login page.
    """
    row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == hash_token(payload.token))
        .first()
    )
    if not row or row.used_at is not None:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has already been used.")
    if row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This reset link has expired. Ask for a new one.")

    if row.user_id is not None:
        account = db.query(User).filter(User.id == row.user_id).first()
        account_type = "org_user"
    else:
        account = db.query(PlatformAdmin).filter(PlatformAdmin.id == row.platform_admin_id).first()
        account_type = "platform_admin"
    if account is None:
        raise HTTPException(status_code=400, detail="This reset link no longer matches an account.")

    account.password_hash = hash_password(payload.new_password)
    row.used_at = datetime.now(timezone.utc)
    db.commit()

    return PasswordResetCompleteResponse(
        account_type=account_type,
        detail="Password updated. You can now sign in with your new password.",
    )

@router.get("/me")
def org_me(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Who am I + my events360.* grants — powers the org dashboard's tab
    gating, computed by the SAME effective_permissions the enforcement
    uses. Only control-plane keys ship here; app grants (eventnxt.*) reach
    their apps through /oauth/userinfo instead.
    """
    eff = effective_permissions(db, user)
    scoped = lambda keys: sorted(k for k in keys if k.startswith("events360."))  # noqa: E731
    return {
        "user_id": str(user.id),
        "organization_id": str(user.organization_id),
        "name": user.name,
        "role": user.role.value,
        "permissions": {
            "all": eff["all"],
            "org_wide": scoped(eff["org_wide"]),
            "by_event": {ev: scoped(keys) for ev, keys in eff["by_event"].items() if scoped(keys)},
        },
    }