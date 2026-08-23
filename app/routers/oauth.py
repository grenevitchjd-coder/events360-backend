from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.organization import Organization
from app.models.oauth_client import OAuthClient
from app.models.oauth_authorization_code import OAuthAuthorizationCode
from app.schemas.oauth import (
    OAuthAuthorizeRequest,
    OAuthAuthorizeResponse,
    OAuthTokenRequest,
    OAuthTokenResponse,
    OAuthUserInfoResponse,
)
from app.services.security import generate_oauth_code, verify_password, create_access_token
from app.services.deps import get_current_user, get_current_oauth_user

router = APIRouter(prefix="/oauth", tags=["oauth"])

AUTH_CODE_LIFETIME_MINUTES = 10
ACCESS_TOKEN_LIFETIME_MINUTES = 60


@router.post("/authorize", response_model=OAuthAuthorizeResponse)
def authorize(
    payload: OAuthAuthorizeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Called by the Events360 frontend (not the downstream app directly) once
    it has confirmed the org user is logged in. Issues a short-lived,
    single-use code the frontend then redirects the browser to the
    downstream app's redirect_uri with.
    """
    client = db.query(OAuthClient).filter(OAuthClient.client_id == payload.client_id).first()
    if not client:
        raise HTTPException(status_code=400, detail="Unknown client_id.")

    allowed_uris = [u.strip() for u in client.redirect_uris.split(",")]
    if payload.redirect_uri not in allowed_uris:
        raise HTTPException(status_code=400, detail="redirect_uri is not registered for this client.")

    code = generate_oauth_code()
    db.add(
        OAuthAuthorizationCode(
            code=code,
            client_id=client.id,
            user_id=user.id,
            redirect_uri=payload.redirect_uri,
            scope=payload.scope,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=AUTH_CODE_LIFETIME_MINUTES),
        )
    )
    db.commit()
    return OAuthAuthorizeResponse(code=code, state=payload.state)


@router.post("/token", response_model=OAuthTokenResponse)
def token(payload: OAuthTokenRequest, db: Session = Depends(get_db)):
    """
    Called by the downstream app's BACKEND (server-to-server, not the
    browser) to exchange a code for an access token. Requires the client
    secret, so only the real downstream app can complete this step even if
    the code were somehow intercepted in the browser redirect.
    """
    if payload.grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail="Only authorization_code grant type is supported.")

    client = db.query(OAuthClient).filter(OAuthClient.client_id == payload.client_id).first()
    if not client or not verify_password(payload.client_secret, client.client_secret_hash):
        raise HTTPException(status_code=401, detail="Invalid client credentials.")

    auth_code = (
        db.query(OAuthAuthorizationCode)
        .filter(OAuthAuthorizationCode.code == payload.code, OAuthAuthorizationCode.client_id == client.id)
        .first()
    )
    if not auth_code:
        raise HTTPException(status_code=400, detail="Invalid authorization code.")
    if auth_code.used:
        raise HTTPException(status_code=400, detail="This authorization code has already been used.")
    if auth_code.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This authorization code has expired.")
    if auth_code.redirect_uri != payload.redirect_uri:
        raise HTTPException(status_code=400, detail="redirect_uri does not match the original request.")

    auth_code.used = True
    db.commit()

    access_token = create_access_token(
        subject=str(auth_code.user_id),
        extra_claims={"type": "oauth_access", "client_id": payload.client_id},
        expires_minutes=ACCESS_TOKEN_LIFETIME_MINUTES,
    )
    return OAuthTokenResponse(access_token=access_token, expires_in=ACCESS_TOKEN_LIFETIME_MINUTES * 60)


@router.get("/userinfo", response_model=OAuthUserInfoResponse)
def userinfo(db: Session = Depends(get_db), user: User = Depends(get_current_oauth_user)):
    """
    Called by the downstream app's backend on each authenticated request
    (token introspection pattern) to verify the token and get the identity
    behind it — no shared secret needed between services.
    """
    org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    return OAuthUserInfoResponse(
        user_id=str(user.id),
        organization_id=str(user.organization_id),
        name=user.name,
        email=user.email,
        role=user.role.value,
    )