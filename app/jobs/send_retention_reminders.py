"""
Sends a reminder email 14 days before an event's data is scheduled for
deletion, to that org's owner/admins. Only sends once per event (guarded
by retention_reminder_sent_at).

Retention counts from the event's END (multi-day events shouldn't have
their data eligible for deletion while still in progress) — falls back to
start_date if no end_date is set.

Intended to run daily via Heroku Scheduler:
    python -m app.jobs.send_retention_reminders
"""

from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models.event import Event
from app.models.user import User, UserRole, UserStatus
from app.services.email import send_email

REMINDER_LEAD_DAYS = 14


def _retention_anchor(event: Event):
    """The date retention counts from: end_date if set, else start_date."""
    return event.end_date or event.start_date


def run():
    now = datetime.now(timezone.utc)

    db = SessionLocal()
    try:
        # Candidates: has SOME date to anchor off, hasn't had a reminder sent yet.
        candidates = (
            db.query(Event)
            .filter(
                (Event.end_date.isnot(None)) | (Event.start_date.isnot(None)),
                Event.retention_reminder_sent_at.is_(None),
            )
            .all()
        )

        sent_count = 0
        for event in candidates:
            anchor = _retention_anchor(event)
            deletion_date = anchor + timedelta(days=event.retention_days)
            reminder_date = deletion_date - timedelta(days=REMINDER_LEAD_DAYS)

            if now < reminder_date:
                continue  # not time yet

            admins = (
                db.query(User)
                .filter(
                    User.organization_id == event.organization_id,
                    User.role.in_([UserRole.ORG_OWNER, UserRole.ORG_ADMIN]),
                    User.status == UserStatus.ACTIVE,
                )
                .all()
            )

            for admin_user in admins:
                send_email(
                    to=admin_user.email,
                    subject=f'Data for "{event.name}" will be deleted soon',
                    body=(
                        f'The data for your event "{event.name}" is scheduled to be deleted on '
                        f"{deletion_date.strftime('%B %d, %Y')} (14 days from now), per your "
                        f"retention setting of {event.retention_days} days after the event ends.\n\n"
                        f"If you'd like to keep this data longer (up to 90 days total), update the "
                        f"retention setting for this event before that date."
                    ),
                )

            event.retention_reminder_sent_at = now
            sent_count += 1

        db.commit()
        print(f"Sent retention reminders for {sent_count} event(s).")
    finally:
        db.close()


if __name__ == "__main__":
    run()