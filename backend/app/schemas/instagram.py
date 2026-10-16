from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class InstagramOAuthURLResponse(BaseModel):
    oauth_url: str
    state: str

class InstagramConnectRequest(BaseModel):
    code: str
    state: str

class InstagramSandboxToggleRequest(BaseModel):
    enabled: bool = True
    username: Optional[str] = "creator_woka_demo"
    followers_count: Optional[int] = 48500
