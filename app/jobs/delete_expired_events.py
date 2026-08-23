"""
Deletes an event's data once its retention window has fully passed
(event_date + retention_days). Cascades to staff_assignments scoped to
that event via ON DELETE CASCADE.

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


def run():
    now = datetime.now(timezone.utc)

    db = SessionLocal()
    try:
        candidates = db.query(Event).filter(Event.event_date.isnot(None)).all()

        deleted_count = 0
        for event in candidates:
            deletion_date = event.event_date + timedelta(days=event.retention_days)
            if now >= deletion_date:
                db.delete(event)
                deleted_count += 1

        db.commit()
        print(f"Deleted {deleted_count} event(s) past their retention window.")
    finally:
        db.close()


if __name__ == "__main__":
    run()