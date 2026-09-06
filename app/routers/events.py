# events360-backend/app/routers/events.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.event import Event, EventStatus
from app.models.user import User
from app.schemas.event import (
    EventCreateRequest,
    EventUpdateRequest,
    EventResponse,
    EventRetentionUpdateRequest,
)
from app.services.deps import require_org_admin

router = APIRouter(prefix="/organizations/{org_id}/events", tags=["events"])


@router.post("", response_model=EventResponse, status_code=201)
def create_event(
    org_id: str,
    payload: EventCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_org_admin),
):
    event = Event(
        organization_id=org_id, name=payload.name, start_date=payload.start_date, end_date=payload.end_date
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("", response_model=list[EventResponse])
def list_events(
    org_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_org_admin),
):
    return db.query(Event).filter(Event.organization_id == org_id).all()


@router.delete("/{event_id}", status_code=204)
def delete_event(
    org_id: str,
    event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_org_admin),
):
    event = db.query(Event).filter(Event.id == event_id, Event.organization_id == org_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    db.delete(event)
    db.commit()


@router.patch("/{event_id}", response_model=EventResponse)
def update_event(
    org_id: str,
    event_id: str,
    payload: EventUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_org_admin),
):
    """
    Edit an event's name and dates — fixing a typo or rescheduling. Locked
    events refuse edits (lock is a superadmin support action; editing around
    it would defeat it). Note for downstream apps: Events360's dates are
    AUTHORITATIVE for EventNXT — day-based setups there follow the new dates
    on their own, but already-issued dated tickets keep their original dates
    (the frontend warns about this when dates change).
    """
    event = db.query(Event).filter(Event.id == event_id, Event.organization_id == org_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    if event.status == EventStatus.LOCKED:
        raise HTTPException(
            status_code=403,
            detail="This event is locked and cannot be edited. Contact support.",
        )

    event.name = payload.name
    event.start_date = payload.start_date
    event.end_date = payload.end_date
    db.commit()
    db.refresh(event)
    return event


@router.patch("/{event_id}/retention", response_model=EventResponse)
def update_event_retention(
    org_id: str,
    event_id: str,
    payload: EventRetentionUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_org_admin),
):
    """
    Lets an org admin extend (or shorten) how long this event's data is kept
    after the event date passes. Capped 1-90 days by the request schema.
    """
    event = db.query(Event).filter(Event.id == event_id, Event.organization_id == org_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    event.retention_days = payload.retention_days
    db.commit()
    db.refresh(event)
    return event