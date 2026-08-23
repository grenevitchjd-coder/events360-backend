from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.event import Event
from app.models.user import User
from app.schemas.event import EventCreateRequest, EventResponse
from app.services.deps import require_org_admin

router = APIRouter(prefix="/organizations/{org_id}/events", tags=["events"])


@router.post("", response_model=EventResponse, status_code=201)
def create_event(
    org_id: str,
    payload: EventCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_org_admin),
):
    event = Event(organization_id=org_id, name=payload.name, event_date=payload.event_date)
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