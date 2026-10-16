import uuid
from datetime import datetime, date, timezone
from sqlalchemy import Column, String, DateTime, Date, ForeignKey, Text, Integer, Float
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class CreatorAnalytics(Base):
    __tablename__ = "creator_analytics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False, index=True, default=date.today)
    followers_count = Column(Integer, nullable=False, default=0)
    following_count = Column(Integer, nullable=False, default=0)
    media_count = Column(Integer, nullable=False, default=0)
    reach_30d = Column(Integer, nullable=False, default=0)
    impressions_30d = Column(Integer, nullable=False, default=0)
    avg_engagement_rate = Column(Float, nullable=False, default=0.0)
    demographics_json = Column(Text, nullable=True)  # JSON string of age, gender, country
    top_posts_json = Column(Text, nullable=True)     # JSON string of top performing posts
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="analytics_snapshots")
