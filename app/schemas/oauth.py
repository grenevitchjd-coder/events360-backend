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


class OAuthUserInfoResponse(BaseModel):
    user_id: str
    organization_id: str
    name: str
    email: str
    role: str


class OAuthEventInfoResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    status: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None