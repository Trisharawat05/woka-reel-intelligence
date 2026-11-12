from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, description="Password at least 6 characters")
    full_name: str = Field(min_length=2, max_length=120)
    role: str = Field(default="CREATOR", description="CREATOR, BRAND, AGENCY")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    avatar_url: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WorkspaceResponse(BaseModel):
    id: str
    name: str
    owner_id: str

    model_config = ConfigDict(from_attributes=True)

class WorkspaceMembershipResponse(BaseModel):
    id: str
    name: str
    owner_id: str
    role_in_workspace: str
    is_active: bool = False

class WorkspaceSelectRequest(BaseModel):
    workspace_id: str = Field(min_length=1)

class OAuth2TokenResponse(BaseModel):
    """Standard OAuth2 bearer token payload returned by form-based /auth/token login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenResponse(OAuth2TokenResponse):
    user: UserResponse
    workspace: WorkspaceResponse

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class TokenRefreshResponse(OAuth2TokenResponse):
    """Token pair returned after rotating a refresh token."""

class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None

class MessageResponse(BaseModel):
    message: str

