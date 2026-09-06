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


# Invites (a brand-new person setting their FIRST password) get a longer
# window than resets: the email may not be opened until tomorrow. Same
# single-use, newest-wins token rows either way.
INVITE_TOKEN_LIFETIME_MINUTES = 7 * 24 * 60


def issue_reset_token(
    db: Session,
    *,
    user: User | None = None,
    platform_admin: PlatformAdmin | None = None,
    created_by_user_id=None,
    created_by_admin_id=None,
    lifetime_minutes: int = RESET_TOKEN_LIFETIME_MINUTES,
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
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=lifetime_minutes),
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

def issue_and_email_invite_link(db: Session, *, user: User, org_name: str, initiated_by: str, created_by_user_id=None) -> str:
    """
    Welcome flow for a newly added person: their account starts with an
    unusable random password, and this email's set-password link (the same
    public /reset-password page) is the ONLY way a first password gets
    created — organizers never type or know anyone's password. 7-day,
    single-use link; "Send reset link" reissues if it lapses. Same 502
    honesty as resets when email can't go out.
    """
    raw_token = issue_reset_token(
        db,
        user=user,
        created_by_user_id=created_by_user_id,
        lifetime_minutes=INVITE_TOKEN_LIFETIME_MINUTES,
    )
    link = build_reset_link(raw_token)

    subject = f"You've been added to {org_name} on Events360"
    body = (
        f"Hi {user.name},\n\n"
        f"{initiated_by} added you to {org_name} on Events360.\n\n"
        f"Set your password to get started:\n{link}\n\n"
        f"This link works once and expires in 7 days. If it lapses, ask your "
        f"organizer to send you a fresh one from the Staff page.\n"
    )

    try:
        sent = email_service.send_email(to=user.email, subject=subject, body=body)
    except (smtplib.SMTPException, OSError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not send the invite email: {exc}",
        )
    if not sent:
        raise HTTPException(
            status_code=502,
            detail="Email is not configured on the server (SMTP settings missing), so the invite could not be sent.",
        )
    return f"Invite sent to {user.email}."