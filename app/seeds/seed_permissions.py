# events360-backend/app/seeds/seed_permissions.py
"""
Seeds the fixed, platform-defined permission catalog. Orgs build custom
Roles out of these — they never create new Permissions themselves.

Run once, after migrations:
    python -m app.seeds.seed_permissions

Safe to re-run: creates any missing permission, updates the category/
description of any that drifted, and RETIRES any catalog key no longer in
this file (removing it from existing roles first). This file is the single
source of truth for what permissions exist.

Key shape: "<app>.<area>.<action>" where action is view or manage
(manage implies view — the Roles UI enforces that), or "<app>.<name>"
for single-toggle permissions like check-in. `category` is the app name,
used to group the Roles UI; areas are parsed from the key itself, so
adding a page to EventNXT never changes this catalog — pages join areas.

History: the original six guessed keys (manage_events, manage_staff,
manage_guests, send_emails, view_reports, manage_billing) predate EventNXT
existing and mapped to nothing real; re-running this seed retires them.
"""

from app.database import SessionLocal
from app.models.permission import Permission
from app.models.role import role_permissions

# (key, category, description)
CATALOG = [
    # --- EventNXT: five areas x view/manage, plus check-in ---
    ("eventnxt.setup.view", "EventNXT",
     "See event configuration — Event settings, Tickets & seating, Guest types, Seating summary"),
    ("eventnxt.setup.manage", "EventNXT",
     "Change event configuration — settings, ticket types, seating, guest types"),
    ("eventnxt.guests.view", "EventNXT",
     "See the Invites and Allotments pages"),
    ("eventnxt.guests.manage", "EventNXT",
     "Add and manage invited guests, allotments, and their tickets"),
    ("eventnxt.guest_list.view", "EventNXT",
     "See the Guest list roster — who's coming, codes, seats, statuses"),
    ("eventnxt.guest_list.manage", "EventNXT",
     "Adjust guests on the Guest list — change status, re-send tickets"),
    ("eventnxt.promotion.view", "EventNXT",
     "See Promos and Referral setup"),
    ("eventnxt.promotion.manage", "EventNXT",
     "Create and edit promo codes and referral deals"),
    ("eventnxt.money.view", "EventNXT",
     "See sales, earnings, promo tracking, and referral payouts"),
    ("eventnxt.money.manage", "EventNXT",
     "Act on money — refunds, mark payouts paid, release the reserve"),
    ("eventnxt.checkin", "EventNXT",
     "Check guests in at the door — the scanner page and Guest list check-in"),
]


def run():
    db = SessionLocal()
    try:
        catalog_keys = {key for key, _, _ in CATALOG}

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

        # Retire anything not in the catalog: pull it out of every role,
        # then delete it. Roles keep their other permissions untouched.
        retired = 0
        stale = db.query(Permission).filter(Permission.key.notin_(catalog_keys)).all()
        for perm in stale:
            db.execute(role_permissions.delete().where(role_permissions.c.permission_id == perm.id))
            db.delete(perm)
            retired += 1
            print(f"Retired permission: {perm.key}")

        db.commit()
        unchanged = len(CATALOG) - created - updated
        print(f"Permissions: {created} created, {updated} updated, {unchanged} unchanged, {retired} retired.")
    finally:
        db.close()


if __name__ == "__main__":
    run()