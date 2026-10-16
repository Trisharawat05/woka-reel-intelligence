import json
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.campaign import (
    CampaignCreate, CampaignResponse,
    ApplicationCreate, ApplicationResponse,
    DeliverableSubmitRequest, DeliverableResponse
)
from app.services.auth_service import get_or_create_workspace
from app.services.campaign_service import (
    create_campaign, list_campaigns, get_campaign,
    apply_to_campaign, list_applications_for_creator,
    list_applications_for_campaign, update_application_status,
    submit_deliverable
)
from app.security import get_current_user, require_roles

router = APIRouter(prefix="/campaigns", tags=["Brand Marketplace & Campaigns"])

def to_campaign_response(c) -> CampaignResponse:
    try:
        reqs = json.loads(c.required_deliverables)
    except Exception:
        reqs = []
    
    brand_name = c.brand_workspace.name if c.brand_workspace else "Brand Partner"
    apps_count = len(c.applications) if c.applications else 0
    return CampaignResponse(
        id=c.id,
        brand_workspace_id=c.brand_workspace_id,
        title=c.title,
        description=c.description,
        niche=c.niche,
        budget_min=c.budget_min,
        budget_max=c.budget_max,
        required_deliverables=reqs,
        submission_deadline=c.submission_deadline,
        status=c.status,
        created_at=c.created_at,
        brand_name=brand_name,
        applications_count=apps_count
    )

@router.get("", response_model=List[CampaignResponse])
def get_campaigns(niche: Optional[str] = Query(None), db: Session = Depends(get_db)):
    campaigns = list_campaigns(db, niche=niche)
    return [to_campaign_response(c) for c in campaigns]

@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def post_campaign(payload: CampaignCreate, current_user: User = Depends(require_roles(["BRAND", "AGENCY", "ADMIN"])), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    camp = create_campaign(db, workspace.id, payload)
    return to_campaign_response(camp)

@router.get("/my-applications", response_model=List[ApplicationResponse])
def get_my_applications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    apps = list_applications_for_creator(db, workspace.id)
    return [
        ApplicationResponse(
            id=a.id,
            campaign_id=a.campaign_id,
            creator_workspace_id=a.creator_workspace_id,
            pitch_text=a.pitch_text,
            proposed_rate=a.proposed_rate,
            status=a.status,
            created_at=a.created_at,
            campaign_title=a.campaign.title if a.campaign else None
        )
        for a in apps
    ]

@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_one_campaign(campaign_id: str, db: Session = Depends(get_db)):
    camp = get_campaign(db, campaign_id)
    return to_campaign_response(camp)

@router.post("/{campaign_id}/apply", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def apply_campaign(campaign_id: str, payload: ApplicationCreate, current_user: User = Depends(require_roles(["CREATOR", "AGENCY", "ADMIN"])), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    app_record = apply_to_campaign(db, campaign_id, workspace.id, payload)
    return ApplicationResponse(
        id=app_record.id,
        campaign_id=app_record.campaign_id,
        creator_workspace_id=app_record.creator_workspace_id,
        pitch_text=app_record.pitch_text,
        proposed_rate=app_record.proposed_rate,
        status=app_record.status,
        created_at=app_record.created_at,
        campaign_title=app_record.campaign.title if app_record.campaign else None
    )

@router.get("/{campaign_id}/applications", response_model=List[ApplicationResponse])
def get_campaign_proposals(campaign_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspace = get_or_create_workspace(db, current_user)
    apps = list_applications_for_campaign(db, campaign_id, workspace.id)
    return [
        ApplicationResponse(
            id=a.id,
            campaign_id=a.campaign_id,
            creator_workspace_id=a.creator_workspace_id,
            creator_name=a.creator_workspace.name if a.creator_workspace else "Creator",
            pitch_text=a.pitch_text,
            proposed_rate=a.proposed_rate,
            status=a.status,
            created_at=a.created_at
        )
        for a in apps
    ]

@router.put("/applications/{application_id}/status", response_model=ApplicationResponse)
def change_application_status(
    application_id: str,
    new_status: str = Query(..., pattern="^(ACCEPTED|REJECTED|COMPLETED)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace = get_or_create_workspace(db, current_user)
    app_record = update_application_status(db, application_id, workspace.id, new_status)
    return ApplicationResponse(
        id=app_record.id,
        campaign_id=app_record.campaign_id,
        creator_workspace_id=app_record.creator_workspace_id,
        pitch_text=app_record.pitch_text,
        proposed_rate=app_record.proposed_rate,
        status=app_record.status,
        created_at=app_record.created_at
    )

@router.post("/applications/{application_id}/deliverables", response_model=DeliverableResponse)
def submit_campaign_deliverable(
    application_id: str,
    payload: DeliverableSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workspace = get_or_create_workspace(db, current_user)
    deliv = submit_deliverable(db, application_id, workspace.id, payload)
    return DeliverableResponse.model_validate(deliv)
