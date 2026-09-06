# events360-backend/app/services/permissions.py
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.staff_assignment import StaffAssignment
from app.models.role import Role, role_permissions
from app.models.permission import Permission


def effective_permissions(db: Session, user: User) -> dict:
    """
    The user's complete permission picture, in one shape:

        {"all": True,  "org_wide": set(), "by_event": {}}          # owner/org_admin
        {"all": False, "org_wide": {keys}, "by_event": {id: {keys}}}  # staff

    org_owner and org_admin implicitly have every permission within their
    own org — "all" short-circuits, no assignment lookup. Staff grants come
    from their StaffAssignments: event_id null = org-wide, else scoped to
    that one event (keyed here by the event id as a string).

    THIS is the single source of truth for what a user can do:
    user_has_permission() below derives from it, and /oauth/userinfo ships
    it to downstream apps — so what an app DISPLAYS (greyed sidebar) and
    what this backend ENFORCES can never drift. Change access logic here
    and only here.
    """
    if user.role.value in ("org_owner", "org_admin"):
        return {"all": True, "org_wide": set(), "by_event": {}}

    rows = (
        db.query(Permission.key, StaffAssignment.event_id)
        .select_from(StaffAssignment)
        .join(Role, StaffAssignment.role_id == Role.id)
        .join(role_permissions, Role.id == role_permissions.c.role_id)
        .join(Permission, role_permissions.c.permission_id == Permission.id)
        .filter(StaffAssignment.user_id == user.id)
        .all()
    )

    org_wide: set = set()
    by_event: dict = {}
    for key, event_id in rows:
        if event_id is None:
            org_wide.add(key)
        else:
            by_event.setdefault(str(event_id), set()).add(key)
    return {"all": False, "org_wide": org_wide, "by_event": by_event}


def user_has_permission(db: Session, user: User, permission_key: str, event_id: str | None = None) -> bool:
    """
    True if the user holds the permission — org-wide, or scoped to the given
    event. Derived from effective_permissions() so enforcement and the
    payload downstream apps display are the same computation.
    """
    eff = effective_permissions(db, user)
    if eff["all"]:
        return True
    if permission_key in eff["org_wide"]:
        return True
    if event_id is not None and permission_key in eff["by_event"].get(str(event_id), set()):
        return True
    return False