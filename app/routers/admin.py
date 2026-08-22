from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.organization import Organization, OrganizationStatus
from app.models.platform_admin import PlatformAdmin, PlatformAdminStatus
from app.models.approval_log import OrganizationApprovalLog, ApprovalDecision
from app.schemas.auth import TokenResponse
from app.schemas.admin import PendingOrganizationResponse, ApprovalDecisionRequest
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
                owner_email=owner.email if owner else "unknown",
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