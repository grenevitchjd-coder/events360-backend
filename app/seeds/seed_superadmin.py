"""
Bootstraps the first PlatformAdmin (superadmin) account, since there's no
existing admin to approve one otherwise.

Run once, after migrations, via:
    python -m app.seeds.seed_superadmin

Reads credentials from environment variables rather than hardcoding them,
so this file is safe to commit — set these in Heroku config vars before
running (or as a one-off local .env for dev):

    SUPERADMIN_NAME
    SUPERADMIN_EMAIL
    SUPERADMIN_PASSWORD
"""

import os
import sys

from app.database import SessionLocal
from app.models.platform_admin import PlatformAdmin, PlatformAdminRole, PlatformAdminStatus
from app.services.security import hash_password, validate_password_policy


def run():
    name = os.environ.get("SUPERADMIN_NAME")
    email = os.environ.get("SUPERADMIN_EMAIL")
    password = os.environ.get("SUPERADMIN_PASSWORD")

    if not all([name, email, password]):
        print(
            "Missing SUPERADMIN_NAME / SUPERADMIN_EMAIL / SUPERADMIN_PASSWORD "
            "environment variables. Aborting.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        validate_password_policy(password)
    except ValueError as e:
        print(f"Password policy violation: {e}", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        existing = db.query(PlatformAdmin).filter(PlatformAdmin.email == email).first()
        if existing:
            print(f"A PlatformAdmin with email {email} already exists. Skipping.")
            return

        admin = PlatformAdmin(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=PlatformAdminRole.SUPERADMIN,
            status=PlatformAdminStatus.ACTIVE,
            created_by=None,  # bootstrap account, no creator
        )
        db.add(admin)
        db.commit()
        print(f"Superadmin account created: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    run()