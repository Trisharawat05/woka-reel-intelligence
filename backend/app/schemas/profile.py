from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class ProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=2, max_length=120)
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    niches: Optional[List[str]] = None
    location: Optional[str] = None
    rate_reel: Optional[float] = Field(None, ge=0)
    rate_story: Optional[float] = Field(None, ge=0)
    rate_bundle: Optional[float] = Field(None, ge=0)
    is_public: Optional[bool] = None

class ProfileResponse(BaseModel):
    id: str
    workspace_id: str
    slug: str
    display_name: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    niches: List[str]
    location: Optional[str] = None
    rate_reel: float
    rate_story: float
    rate_bundle: float
    is_verified: bool
    is_public: bool
    followers_count: int
    engagement_rate: float
    total_reach_30d: int

    model_config = ConfigDict(from_attributes=True)

class PublicInquiryRequest(BaseModel):
    brand_name: str = Field(min_length=2)
    contact_email: str
    budget: str
    project_scope: str
    message: str
