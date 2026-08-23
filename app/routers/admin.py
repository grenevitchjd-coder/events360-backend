from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.organization import Organization, OrganizationStatus
from app.models.event import Event, EventStatus
from app.models.platform_admin import PlatformAdmin, PlatformAdminStatus
from app.models.approval_log import OrganizationApprovalLog, ApprovalDecision
from app.schemas.auth import TokenResponse
from app.schemas.admin import PendingOrganizationResponse, ApprovalDecisionRequest
from app.schemas.event import EventResponse
from app.services.security import verify_password, create_access_token
from app.services.deps import get_current_platform_admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/login", response_model=TokenResponse)
def admin_login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    admin = db.query(PlatformAdmin).filter(PlatformAdmin.email == form_data.username).first()
    if not admin or not verify_password(form_data.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if admin.status != PlatformAdminStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="This admin account has been disabled.")

    token = create_access_token(
        subject=str(admin.id),
        extra_claims={"type": "platform_admin", "role": admin.role.value},
    )
    return TokenResponse(access_token=token)


@router.get("/organizations/pending", response_model=list[PendingOrganizationResponse])
def list_pending_organizations(
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
):
    pending = (
        db.query(Organization).filter(Organization.status == OrganizationStatus.PENDING_APPROVAL).all()
    )
    results = []
    for org in pending:
        owner = next((u for u in org.users if u.role.value == "org_owner"), None)
        results.append(
            PendingOrganizationResponse(
                id=org.id,
                name=org.name,
                owner_name=owner.name if owner else "unknown",
                owner_email=owner.email if owner else "unknown",
                status=org.status.value,
                created_at=org.created_at.isoformat(),
            )
        )
    return results


@router.get("/organizations", response_model=list[PendingOrganizationResponse])
def list_all_organizations(
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
):
    """All orgs regardless of status — the dashboard's main org browser,
    used for lock/unlock/delete actions on already-approved orgs."""
    orgs = db.query(Organization).all()
    results = []
    for org in orgs:
        owner = next((u for u in org.users if u.role.value == "org_owner"), None)
        results.append(
            PendingOrganizationResponse(
                id=org.id,
                name=org.name,
                owner_name=owner.name if owner else "unknown",
                owner_email=owner.email if owner else "unknown",
                status=org.status.value,
                created_at=org.created_at.isoformat(),
            )
        )
    return results


@router.post("/organizations/{org_id}/approve")
def approve_organization(
    org_id: str,
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(get_current_platform_admin),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")

    org.status = OrganizationStatus.ACTIVE
    db.add(
        OrganizationApprovalLog(
            organization_id=org.id,
            organization_name_snapshot=org.name,
            decision=ApprovalDecision.APPROVED,
            reviewed_by=admin.id,
            notes=payload.notes,
        )
    )
    db.commit()
    return {"status": "approved"}


@router.post("/organizations/{org_id}/deny")
def deny_organization(
    org_id: str,
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(get_current_platform_admin),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")

    org.status = OrganizationStatus.DENIED
    db.add(
        OrganizationApprovalLog(
            organization_id=org.id,
            organization_name_snapshot=org.name,
            decision=ApprovalDecision.DENIED,
            reviewed_by=admin.id,
            notes=payload.notes,
        )
    )
    db.commit()
    return {"status": "denied"}


@router.delete("/organizations/{org_id}", status_code=204)
def delete_organization(
    org_id: str,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
):
    """
    Superadmin (or support_admin — both have full operational access) can
    delete any organization, regardless of status. Cascades to every
    related record at the database level.
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")
    db.delete(org)
    db.commit()


@router.delete("/organizations/{org_id}/events/{event_id}", status_code=204)
def delete_event_as_admin(
    org_id: str,
    event_id: str,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
):
    event = db.query(Event).filter(Event.id == event_id, Event.organization_id == org_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    db.delete(event)
    db.commit()


@router.get("/organizations/{org_id}/events", response_model=list[EventResponse])
def list_events_as_admin(
    org_id: str,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
):
    """Powers the expandable event rows under each org in the dashboard."""
    return db.query(Event).filter(Event.organization_id == org_id).all()


@router.post("/organizations/{org_id}/events/{event_id}/lock", response_model=EventResponse)
def lock_event(
    org_id: str,
    event_id: str,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
):
    """
    Superadmin/support action only — org admins have no self-service way to
    lock their own events. Sets a status flag; actual enforcement against
    event-scoped actions (blocking guest management, etc.) is future work
    once EventNXT exists and checks event status via the API.
    """
    event = db.query(Event).filter(Event.id == event_id, Event.organization_id == org_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    event.status = EventStatus.LOCKED
    db.commit()
    db.refresh(event)
    return event


@router.post("/organizations/{org_id}/events/{event_id}/unlock", response_model=EventResponse)
def unlock_event(
    org_id: str,
    event_id: str,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
):
    event = db.query(Event).filter(Event.id == event_id, Event.organization_id == org_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    event.status = EventStatus.ACTIVE
    db.commit()
    db.refresh(event)
    return event


@router.post("/organizations/{org_id}/lock")
def lock_organization(
    org_id: str,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
):
    """
    Manual lock, e.g. for a lapsed subscription. Blocks access but preserves
    all data — distinct from deletion. (Automatic triggering off a real
    billing/renewal event is future work, once billing itself is built —
    this endpoint is the mechanism a future webhook would call.)
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")
    org.status = OrganizationStatus.LOCKED
    db.commit()
    return {"status": "locked"}


@router.post("/organizations/{org_id}/unlock")
def unlock_organization(
    org_id: str,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")
    org.status = OrganizationStatus.ACTIVE
    db.commit()
    return {"status": "active"}