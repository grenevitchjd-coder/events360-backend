from sqlalchemy.orm import Session

from app.models.user import User
from app.models.staff_assignment import StaffAssignment
from app.models.role import Role, role_permissions
from app.models.permission import Permission


def user_has_permission(db: Session, user: User, permission_key: str, event_id: str | None = None) -> bool:
    """
    org_owner and org_admin implicitly have every permission within their
    own org — no need to check StaffAssignment for them.

    staff users need an active StaffAssignment to a Role that grants the
    given permission, and that assignment must match the scope: either
    org-wide (event_id is null on the assignment) or the specific event
    being acted on.
    """
    if user.role.value in ("org_owner", "org_admin"):
        return True

    query = (
        db.query(StaffAssignment)
        .join(Role, StaffAssignment.role_id == Role.id)
        .join(role_permissions, Role.id == role_permissions.c.role_id)
        .join(Permission, role_permissions.c.permission_id == Permission.id)
        .filter(StaffAssignment.user_id == user.id, Permission.key == permission_key)
    )

    # Org-wide assignments (event_id is null) grant the permission everywhere.
    # Event-scoped assignments only grant it for that specific event.
    query = query.filter(
        (StaffAssignment.event_id.is_(None))
        | (StaffAssignment.event_id == event_id if event_id else False)
    )

    return db.query(query.exists()).scalar()