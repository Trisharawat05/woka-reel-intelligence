import json
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.campaign import BrandCampaign, CampaignApplication, CampaignDeliverable
from app.models.user import Workspace
from app.models.notification import Notification
from app.schemas.campaign import CampaignCreate, ApplicationCreate, DeliverableSubmitRequest, DeliverableReviewRequest

def create_campaign(db: Session, brand_workspace_id: str, payload: CampaignCreate) -> BrandCampaign:
    deliverables_json = json.dumps(payload.required_deliverables)
    campaign = BrandCampaign(
        brand_workspace_id=brand_workspace_id,
        title=payload.title,
        description=payload.description,
        niche=payload.niche,
        budget_min=payload.budget_min,
        budget_max=payload.budget_max,
        required_deliverables=deliverables_json,
        submission_deadline=payload.submission_deadline,
        status="OPEN"
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign

def list_campaigns(db: Session, niche: Optional[str] = None) -> List[BrandCampaign]:
    query = db.query(BrandCampaign).filter(BrandCampaign.status == "OPEN")
    if niche and niche.lower() != "all":
        query = query.filter(BrandCampaign.niche.ilike(f"%{niche}%"))
    return query.order_by(BrandCampaign.created_at.desc()).all()

def get_campaign(db: Session, campaign_id: str) -> BrandCampaign:
    campaign = db.query(BrandCampaign).filter(BrandCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return campaign

def apply_to_campaign(db: Session, campaign_id: str, creator_workspace_id: str, payload: ApplicationCreate) -> CampaignApplication:
    campaign = get_campaign(db, campaign_id)
    
    if campaign.brand_workspace_id == creator_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Brand cannot apply to its own campaign"
        )

    # Check if already applied
    existing = db.query(CampaignApplication).filter(
        CampaignApplication.campaign_id == campaign_id,
        CampaignApplication.creator_workspace_id == creator_workspace_id
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have already submitted an application to this campaign")

    app_record = CampaignApplication(
        campaign_id=campaign_id,
        creator_workspace_id=creator_workspace_id,
        pitch_text=payload.pitch_text,
        proposed_rate=payload.proposed_rate,
        status="APPLIED"
    )
    db.add(app_record)

    # Notify brand owner
    brand_ws = db.query(Workspace).filter(Workspace.id == campaign.brand_workspace_id).first()
    if brand_ws:
        notif = Notification(
            user_id=brand_ws.owner_id,
            title="New Campaign Proposal Received!",
            message=f"A creator submitted a proposal for '{campaign.title}' quoting ${payload.proposed_rate:.2f}.",
            category="CAMPAIGN",
            link="/dashboard/campaigns"
        )
        db.add(notif)

    db.commit()
    db.refresh(app_record)
    return app_record

def list_applications_for_creator(db: Session, creator_workspace_id: str) -> List[CampaignApplication]:
    return db.query(CampaignApplication).filter(
        CampaignApplication.creator_workspace_id == creator_workspace_id
    ).order_by(CampaignApplication.created_at.desc()).all()

def list_applications_for_campaign(db: Session, campaign_id: str, brand_workspace_id: str) -> List[CampaignApplication]:
    campaign = get_campaign(db, campaign_id)
    if campaign.brand_workspace_id != brand_workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view these applications")
    return db.query(CampaignApplication).filter(
        CampaignApplication.campaign_id == campaign_id
    ).order_by(CampaignApplication.created_at.desc()).all()

def update_application_status(db: Session, application_id: str, brand_workspace_id: str, new_status: str) -> CampaignApplication:
    app_record = db.query(CampaignApplication).filter(CampaignApplication.id == application_id).first()
    if not app_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    
    if app_record.campaign.brand_workspace_id != brand_workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this application")

    valid_transitions = {
        "APPLIED": ["ACCEPTED", "REJECTED"],
        "ACCEPTED": ["COMPLETED"]
    }
    allowed = valid_transitions.get(app_record.status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid state transition: Cannot change application from '{app_record.status}' to '{new_status}'"
        )

    app_record.status = new_status
    
    # Notify creator
    creator_ws = db.query(Workspace).filter(Workspace.id == app_record.creator_workspace_id).first()
    if creator_ws:
        notif = Notification(
            user_id=creator_ws.owner_id,
            title=f"Campaign Application Update: {new_status}!",
            message=f"Your proposal for '{app_record.campaign.title}' has been updated to {new_status}.",
            category="CAMPAIGN",
            link="/dashboard/campaigns"
        )
        db.add(notif)

    db.commit()
    db.refresh(app_record)
    return app_record

def submit_deliverable(db: Session, application_id: str, creator_workspace_id: str, payload: DeliverableSubmitRequest) -> CampaignDeliverable:
    app_record = db.query(CampaignApplication).filter(CampaignApplication.id == application_id).first()
    if not app_record or app_record.creator_workspace_id != creator_workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to submit deliverable")

    if app_record.status != "ACCEPTED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deliverables can only be submitted for accepted applications"
        )


    deliverable = CampaignDeliverable(
        application_id=application_id,
        deliverable_type=payload.deliverable_type,
        live_url=payload.live_url,
        preview_asset_url=payload.preview_asset_url,
        status="IN_REVIEW",
        submitted_at=datetime.now(timezone.utc)
    )
    db.add(deliverable)
    db.commit()
    db.refresh(deliverable)
    return deliverable
