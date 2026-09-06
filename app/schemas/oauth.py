# events360-backend/app/schemas/oauth.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class OAuthAuthorizeRequest(BaseModel):
    client_id: str
    redirect_uri: str
    scope: Optional[str] = None
    state: Optional[str] = None


class OAuthAuthorizeResponse(BaseModel):
    code: str
    state: Optional[str] = None


class OAuthTokenRequest(BaseModel):
    grant_type: str  # only "authorization_code" supported
    code: str
    client_id: str
    client_secret: str
    redirect_uri: str


class OAuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class OAuthPermissions(BaseModel):
    """The user's effective grants for the CALLING app (keys are filtered
    to the client's own namespace — EventNXT never sees CastNXT grants).
    all=True means owner/org_admin: implicit everything, lists empty."""

    all: bool
    org_wide: list[str] = []
    by_event: dict[str, list[str]] = {}


class OAuthUserInfoResponse(BaseModel):
    user_id: str
    organization_id: str
    name: str
    email: str
    role: str
    permissions: OAuthPermissions


class OAuthEventInfoResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    status: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None