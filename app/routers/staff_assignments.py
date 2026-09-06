from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.staff_assignment import StaffAssignment
from app.models.user import User
from app.models.role import Role
from app.models.event import Event
from app.schemas.staff_assignment import (
    StaffAssignmentCreateRequest,
    StaffAssignmentUpdateRequest,
    StaffAssignmentResponse,
)
from app.services.permissions import require_org_permission

router = APIRouter(prefix="/organizations/{org_id}/staff-assignments", tags=["staff"])


@router.post("", response_model=StaffAssignmentResponse, status_code=201)
def create_staff_assignment(
    org_id: str,
    payload: StaffAssignmentCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_org_permission("events360.staff.manage")),
):
    # Staff holding events360.staff.manage can hand out EXISTING roles to
    # others but never to themselves — otherwise the grant quietly includes
    # every role in the org (self-assign Finance, walk into money). Owners
    # and org admins are exempt (they implicitly have everything anyway).
    if admin.role.value == "staff" and str(payload.user_id) == str(admin.id):
        raise HTTPException(status_code=403, detail="You can't assign roles to yourself.")

    # Validate the target user, role, and (optional) event all belong to this org —
    # prevents assigning someone else's user to your role, or vice versa.
    target_user = db.query(User).filter(User.id == payload.user_id, User.organization_id == org_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found in this organization.")

    role = db.query(Role).filter(Role.id == payload.role_id, Role.organization_id == org_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found in this organization.")

    if payload.event_id:
        event = (
            db.query(Event).filter(Event.id == payload.event_id, Event.organization_id == org_id).first()
        )
        if not event:
            raise HTTPException(status_code=404, detail="Event not found in this organization.")

    assignment = StaffAssignment(
        user_id=payload.user_id, role_id=payload.role_id, event_id=payload.event_id
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("", response_model=list[StaffAssignmentResponse])
def list_staff_assignments(
    org_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_org_permission("events360.staff.view")),
):
    return (
        db.query(StaffAssignment)
        .join(User, StaffAssignment.user_id == User.id)
        .filter(User.organization_id == org_id)
        .all()
    )


@router.delete("/{assignment_id}", status_code=204)
def delete_staff_assignment(
    org_id: str,
    assignment_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_org_permission("events360.staff.manage")),
):
    assignment = (
        db.query(StaffAssignment)
        .join(User, StaffAssignment.user_id == User.id)
        .filter(StaffAssignment.id == assignment_id, User.organization_id == org_id)
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Staff assignment not found.")
    db.delete(assignment)
    db.commit()

@router.patch("/{assignment_id}", response_model=StaffAssignmentResponse)
def update_staff_assignment(
    org_id: str,
    assignment_id: str,
    payload: StaffAssignmentUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_org_permission("events360.staff.manage")),
):
    """
    Change an existing assignment's role and/or scope in place — so
    "promote Door staff to Guest manager" or "widen this grant from one
    event to org-wide" is one edit, not a remove-and-re-add. The person on
    the assignment never changes here (that IS a remove-and-re-add,
    deliberately). Same guards as creating: everything must belong to this
    org, and staff can't touch their own grants.
    """
    assignment = (
        db.query(StaffAssignment)
        .join(User, StaffAssignment.user_id == User.id)
        .filter(StaffAssignment.id == assignment_id, User.organization_id == org_id)
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found in this organization.")

    if admin.role.value == "staff" and str(assignment.user_id) == str(admin.id):
        raise HTTPException(status_code=403, detail="You can't change your own role assignments.")

    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="Nothing to change.")

    if "role_id" in fields and fields["role_id"]:
        role = db.query(Role).filter(Role.id == fields["role_id"], Role.organization_id == org_id).first()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found in this organization.")
        assignment.role_id = fields["role_id"]

    if "event_id" in fields:
        if fields["event_id"]:
            event = (
                db.query(Event).filter(Event.id == fields["event_id"], Event.organization_id == org_id).first()
            )
            if not event:
                raise HTTPException(status_code=404, detail="Event not found in this organization.")
        assignment.event_id = fields["event_id"]  # null = org-wide

    db.commit()
    db.refresh(assignment)
    return assignment