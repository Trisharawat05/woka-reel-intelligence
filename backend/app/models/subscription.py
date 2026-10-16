import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

def default_period_end():
    return datetime.now(timezone.utc) + timedelta(days=30)

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, unique=True, index=True)
    plan_tier = Column(String(30), nullable=False, default="FREE")  # FREE, PRO, AGENCY
    status = Column(String(30), nullable=False, default="ACTIVE")  # ACTIVE, TRIALING, PAST_DUE, CANCELLED
    dm_limit_monthly = Column(Integer, nullable=False, default=50)
    dm_used_monthly = Column(Integer, nullable=False, default=0)
    ai_limit_monthly = Column(Integer, nullable=False, default=10)
    ai_used_monthly = Column(Integer, nullable=False, default=0)
    current_period_end = Column(DateTime(timezone=True), default=default_period_end, nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="subscription")
