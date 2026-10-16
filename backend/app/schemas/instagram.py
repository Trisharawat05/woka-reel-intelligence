from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

class InstagramAccountResponse(BaseModel):
    id: str
    workspace_id: str
    ig_user_id: str
    username: str
    name: Optional[str] = None
    profile_pic_url: Optional[str] = None
    is_connected: bool
    is_sandbox: bool
    followers_count: int
    media_count: int
    token_expires_at: Optional[datetime] = None
    granted_permissions: Optional[str] = None
    is_token_expired: Optional[bool] = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InstagramOAuthURLResponse(BaseModel):
    oauth_url: str
    state: str
    scopes_requested: List[str]
    expires_in_seconds: int = 900


class InstagramConnectRequest(BaseModel):
    code: str = Field(..., description="Authorization code from Meta OAuth redirect")
    state: str = Field(..., description="HMAC-signed CSRF state parameter")
    redirect_uri: Optional[str] = Field(default=None, description="Optional redirect URI matching the authorization request")


class InstagramStatusResponse(BaseModel):
    is_connected: bool
    account: Optional[InstagramAccountResponse] = None
    has_insights_permission: bool = False
    token_status: str = "ACTIVE"  # "ACTIVE", "EXPIRED", "REVOKED", "MISSING"
    api_version: str = "v21.0"
    message: Optional[str] = None


class InstagramSyncInsightsResponse(BaseModel):
    status: str  # "SUCCESS", "PARTIAL", "FAILED"
    synced_media_count: int
    metric_snapshots_created: int
    synced_at: datetime
    provenance: Dict[str, Any]
    errors: List[str] = []


class InstagramDisconnectResponse(BaseModel):
    status: str
    message: str


class InstagramRefreshTokenResponse(BaseModel):
    status: str
    token_expires_at: Optional[datetime] = None
    message: str


class InstagramSandboxToggleRequest(BaseModel):
    enabled: bool = True
    username: Optional[str] = "creator_woka_demo"
    followers_count: Optional[int] = 48500
