# events360-backend/app/services/password_reset.py
"""
Issues password reset tokens and emails the links. There is deliberately no
self-service "forgot password" flow (the platform has no 2FA yet): links are
only ever issued by an org owner/admin or a platform admin, and delivered by
email to the account's own address — the issuer never knows or transmits the
new password.
"""

import hashlib
import secrets
import smtplib
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models.password_reset_token import PasswordResetToken
from app.models.platform_admin import PlatformAdmin
from app.models.user import User
from app.services import email as email_service

RESET_TOKEN_LIFETIME_MINUTES = 60


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def issue_reset_token(
    db: Session,
    *,
    user: User | None = None,
    platform_admin: PlatformAdmin | None = None,
    created_by_user_id=None,
    created_by_admin_id=None,
) -> str:
    """
    Creates a fresh reset token for the account and COMMITS it, returning the
    raw token (which is never stored — only its hash is). Any previously
    issued tokens for the same account are removed first, so only the newest
    link works. The commit happens BEFORE the email goes out: a link that
    lands in an inbox always has a live row behind it, while a failed send
    merely leaves an unused token that expires on its own.
    """
    if (user is None) == (platform_admin is None):
        raise ValueError("Exactly one of user / platform_admin must be provided.")

    query = db.query(PasswordResetToken)
    if user is not None:
        query = query.filter(PasswordResetToken.user_id == user.id)
    else:
        query = query.filter(PasswordResetToken.platform_admin_id == platform_admin.id)
    query.delete(synchronize_session=False)

    raw_token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            user_id=user.id if user else None,
            platform_admin_id=platform_admin.id if platform_admin else None,
            token_hash=hash_token(raw_token),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_LIFETIME_MINUTES),
            created_by_user_id=created_by_user_id,
            created_by_admin_id=created_by_admin_id,
        )
    )
    db.commit()
    return raw_token


def build_reset_link(raw_token: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}/reset-password?token={raw_token}"


def issue_and_email_reset_link(
    db: Session,
    *,
    user: User | None = None,
    platform_admin: PlatformAdmin | None = None,
    initiated_by: str,
    created_by_user_id=None,
    created_by_admin_id=None,
) -> str:
    """
    The one shared flow behind every send-reset endpoint: issue the token,
    build the link, email it, and report HONESTLY. Raises HTTPException(502)
    with the real cause when the email can't go out (never a silent success —
    the admin clicking the button is being told "the link is on its way").
    Returns the success detail message.
    """
    account = user if user is not None else platform_admin
    raw_token = issue_reset_token(
        db,
        user=user,
        platform_admin=platform_admin,
        created_by_user_id=created_by_user_id,
        created_by_admin_id=created_by_admin_id,
    )
    link = build_reset_link(raw_token)

    subject = "Reset your Events360 password"
    body = (
        f"Hi {account.name},\n\n"
        f"{initiated_by} requested a password reset link for your Events360 account.\n\n"
        f"Choose a new password here:\n{link}\n\n"
        f"This link works once and expires in {RESET_TOKEN_LIFETIME_MINUTES} minutes.\n"
        "If you weren't expecting this, you can ignore it — your current password still works.\n"
    )

    try:
        sent = email_service.send_email(to=account.email, subject=subject, body=body)
    except (smtplib.SMTPException, OSError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"The reset link could not be emailed: {exc}",
        )
    if not sent:
        raise HTTPException(
            status_code=502,
            detail=(
                "Email is not configured on the server (SMTP config vars are missing), "
                "so the reset link could not be sent."
            ),
        )
    return f"Password reset link emailed to {account.email}."