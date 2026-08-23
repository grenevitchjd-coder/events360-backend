"""
Seeds the fixed, platform-defined permission catalog. Orgs build custom
Roles out of these — they never create new Permissions themselves.

Run once, after migrations:
    python -m app.seeds.seed_permissions

Safe to re-run: creates any missing permission, and updates the category/
description of any that already exist to match this file (so changing a
category here and re-running fixes existing deployed data too).
"""

from app.database import SessionLocal
from app.models.permission import Permission

# (key, category, description) — category is purely for grouping the Roles
# UI into sections; has no effect on how permissions are enforced.
CATALOG = [
    ("manage_events", "Events", "Create, edit, and delete events"),
    ("manage_staff", "Staff", "Add, remove, and assign roles to staff members"),
    ("manage_guests", "Guests", "Manage the guest list, RSVPs, and referrals for an event"),
    ("send_emails", "Guests", "Send emails to guests via the platform"),
    ("view_reports", "Reports", "View reporting and analytics"),
    ("manage_billing", "Billing", "Manage the organization's subscription and billing"),
]


def run():
    db = SessionLocal()
    try:
        created = 0
        updated = 0
        for key, category, description in CATALOG:
            existing = db.query(Permission).filter(Permission.key == key).first()
            if existing:
                if existing.category != category or existing.description != description:
                    existing.category = category
                    existing.description = description
                    updated += 1
                continue
            db.add(Permission(key=key, category=category, description=description))
            created += 1
        db.commit()
        unchanged = len(CATALOG) - created - updated
        print(f"Permissions: {created} created, {updated} updated, {unchanged} unchanged.")
    finally:
        db.close()


if __name__ == "__main__":
    run()