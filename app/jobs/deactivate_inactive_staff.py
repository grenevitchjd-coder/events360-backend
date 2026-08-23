"""
Deactivates any `staff`-role User who hasn't logged in for 30+ days.
org_owner and org_admin are exempt (per architecture doc) so they're never
locked out returning to set up next year's event.

Intended to run daily via Heroku Scheduler:
    python -m app.jobs.deactivate_inactive_staff

Safe to run repeatedly — only touches users currently ACTIVE and past the
30-day threshold, so re-running the same day is a no-op for anyone already
processed.
"""

from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models.user import User, UserRole, UserStatus

INACTIVITY_THRESHOLD_DAYS = 30


def run():
    cutoff = datetime.now(timezone.utc) - timedelta(days=INACTIVITY_THRESHOLD_DAYS)

    db = SessionLocal()
    try:
        stale_staff = (
            db.query(User)
            .filter(
                User.role == UserRole.STAFF,
                User.status == UserStatus.ACTIVE,
                User.last_active_at < cutoff,
            )
            .all()
        )

        for user in stale_staff:
            user.status = UserStatus.INACTIVE

        db.commit()
        print(f"Deactivated {len(stale_staff)} staff account(s) inactive for {INACTIVITY_THRESHOLD_DAYS}+ days.")
    finally:
        db.close()


if __name__ == "__main__":
    run()