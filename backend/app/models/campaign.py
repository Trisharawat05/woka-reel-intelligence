import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class BrandCampaign(Base):
    __tablename__ = "brand_campaigns"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    brand_workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    niche = Column(String(60), nullable=False, index=True)
    budget_min = Column(Float, nullable=False, default=100.0)
    budget_max = Column(Float, nullable=False, default=1000.0)
    required_deliverables = Column(Text, nullable=False, default="[]")  # JSON list
    submission_deadline = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(30), nullable=False, default="OPEN")  # OPEN, IN_PROGRESS, COMPLETED, CLOSED
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    brand_workspace = relationship("Workspace", back_populates="brand_campaigns")
    applications = relationship("CampaignApplication", back_populates="campaign", cascade="all, delete-orphan")

class CampaignApplication(Base):
    __tablename__ = "campaign_applications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    campaign_id = Column(String(36), ForeignKey("brand_campaigns.id"), nullable=False, index=True)
    creator_workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    pitch_text = Column(Text, nullable=False)
    proposed_rate = Column(Float, nullable=False, default=0.0)
    status = Column(String(30), nullable=False, default="APPLIED")  # APPLIED, ACCEPTED, REJECTED, COMPLETED
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    campaign = relationship("BrandCampaign", back_populates="applications")
    creator_workspace = relationship("Workspace", back_populates="campaign_applications")
    deliverables = relationship("CampaignDeliverable", back_populates="application", cascade="all, delete-orphan")

class CampaignDeliverable(Base):
    __tablename__ = "campaign_deliverables"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    application_id = Column(String(36), ForeignKey("campaign_applications.id"), nullable=False, index=True)
    deliverable_type = Column(String(50), nullable=False, default="REEL")  # REEL, STORY, POST, CAROUSEL
    live_url = Column(Text, nullable=True)
    preview_asset_url = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="PENDING")  # PENDING, SUBMITTED, IN_REVIEW, APPROVED, REVISION_REQUESTED
    feedback_notes = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    application = relationship("CampaignApplication", back_populates="deliverables")
