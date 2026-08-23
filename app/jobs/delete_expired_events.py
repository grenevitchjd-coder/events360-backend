"""
Deletes an event's data once its retention window has fully passed
(retention anchor + retention_days). Cascades to staff_assignments scoped
to that event via ON DELETE CASCADE.

Retention counts from the event's END (multi-day events shouldn't have
their data eligible for deletion while still in progress) — falls back to
start_date if no end_date is set.

Note: this deletes the Event record Events360 itself owns. Once EventNXT
exists and holds its own guest/referral data for the event, this job will
also need to notify EventNXT (via the OAuth2/API integration, once built)
so it purges its copy too — that's future work tied to the OAuth2 provider
slice, not something this job can do yet.

Intended to run daily via Heroku Scheduler:
    python -m app.jobs.delete_expired_events
"""

from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models.event import Event


def _retention_anchor(event: Event):
    """The date retention counts from: end_date if set, else start_date."""
    return event.end_date or event.start_date


def run():
    now = datetime.now(timezone.utc)

    db = SessionLocal()
    try:
        candidates = db.query(Event).filter(
            (Event.end_date.isnot(None)) | (Event.start_date.isnot(None))
        ).all()

        deleted_count = 0
        for event in candidates:
            anchor = _retention_anchor(event)
            deletion_date = anchor + timedelta(days=event.retention_days)
            if now >= deletion_date:
                db.delete(event)
                deleted_count += 1

        db.commit()
        print(f"Deleted {deleted_count} event(s) past their retention window.")
    finally:
        db.close()


if __name__ == "__main__":
    run()