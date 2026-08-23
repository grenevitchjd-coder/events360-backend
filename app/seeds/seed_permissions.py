"""
Seeds the fixed, platform-defined permission catalog. Orgs build custom
Roles out of these — they never create new Permissions themselves.

Run once, after migrations:
    python -m app.seeds.seed_permissions

Safe to re-run: skips any permission key that already exists.
"""

from app.database import SessionLocal
from app.models.permission import Permission

CATALOG = [
    ("manage_events", "Create, edit, and delete events"),
    ("manage_staff", "Add, remove, and assign roles to staff members"),
    ("manage_guests", "Manage the guest list, RSVPs, and referrals for an event"),
    ("send_emails", "Send emails to guests via the platform"),
    ("view_reports", "View reporting and analytics"),
    ("manage_billing", "Manage the organization's subscription and billing"),
]


def run():
    db = SessionLocal()
    try:
        created = 0
        for key, description in CATALOG:
            existing = db.query(Permission).filter(Permission.key == key).first()
            if existing:
                continue
            db.add(Permission(key=key, description=description))
            created += 1
        db.commit()
        print(f"Seeded {created} new permission(s). {len(CATALOG) - created} already existed.")
    finally:
        db.close()


if __name__ == "__main__":
    run()