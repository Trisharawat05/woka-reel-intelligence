import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class CreatorProfile(Base):
    __tablename__ = "creator_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, unique=True, index=True)
    slug = Column(String(80), nullable=False, unique=True, index=True)
    display_name = Column(String(120), nullable=False)
    bio = Column(Text, nullable=True)
    avatar_url = Column(Text, nullable=True)
    niches = Column(Text, nullable=False, default="[]")  # JSON encoded list of strings
    location = Column(String(100), nullable=True)
    rate_reel = Column(Float, nullable=False, default=350.0)
    rate_story = Column(Float, nullable=False, default=120.0)
    rate_bundle = Column(Float, nullable=False, default=420.0)
    is_verified = Column(Boolean, nullable=False, default=False)
    is_public = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="creator_profile")
