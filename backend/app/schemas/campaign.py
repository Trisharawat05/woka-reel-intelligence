from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class CampaignCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10)
    niche: str = Field(min_length=2, max_length=60)
    budget_min: float = Field(ge=10)
    budget_max: float = Field(ge=10)
    required_deliverables: List[str] = Field(default_factory=list)
    submission_deadline: datetime

class CampaignResponse(BaseModel):
    id: str
    brand_workspace_id: str
    title: str
    description: str
    niche: str
    budget_min: float
    budget_max: float
    required_deliverables: List[str]
    submission_deadline: datetime
    status: str
    created_at: datetime
    brand_name: Optional[str] = None
    applications_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)

class ApplicationCreate(BaseModel):
    pitch_text: str = Field(min_length=10)
    proposed_rate: float = Field(ge=10)

class ApplicationResponse(BaseModel):
    id: str
    campaign_id: str
    creator_workspace_id: str
    creator_name: Optional[str] = None
    creator_handle: Optional[str] = None
    pitch_text: str
    proposed_rate: float
    status: str
    created_at: datetime
    campaign_title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class DeliverableSubmitRequest(BaseModel):
    deliverable_type: str = Field(default="REEL")
    live_url: Optional[str] = None
    preview_asset_url: Optional[str] = None

class DeliverableReviewRequest(BaseModel):
    status: str = Field(description="APPROVED or REVISION_REQUESTED")
    feedback_notes: Optional[str] = None

class DeliverableResponse(BaseModel):
    id: str
    application_id: str
    deliverable_type: str
    live_url: Optional[str] = None
    preview_asset_url: Optional[str] = None
    status: str
    feedback_notes: Optional[str] = None
    submitted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

