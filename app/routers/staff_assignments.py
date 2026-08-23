from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.staff_assignment import StaffAssignment
from app.models.user import User
from app.models.role import Role
from app.models.event import Event
from app.schemas.staff_assignment import StaffAssignmentCreateRequest, StaffAssignmentResponse
from app.services.deps import require_org_admin

router = APIRouter(prefix="/organizations/{org_id}/staff-assignments", tags=["staff"])


@router.post("", response_model=StaffAssignmentResponse, status_code=201)
def create_staff_assignment(
    org_id: str,
    payload: StaffAssignmentCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_org_admin),
):
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
    admin: User = Depends(require_org_admin),
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
    admin: User = Depends(require_org_admin),
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