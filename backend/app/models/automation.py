import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Automation(Base):
    __tablename__ = "automations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    ig_account_id = Column(String(36), ForeignKey("instagram_accounts.id"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    trigger_type = Column(String(30), nullable=False, default="COMMENT")  # COMMENT, STORY_REPLY, MENTION
    target_post_type = Column(String(30), nullable=False, default="ALL_POSTS")  # ALL_POSTS, SPECIFIC_POST, NEXT_POST
    target_post_id = Column(String(100), nullable=True)
    target_post_preview_url = Column(Text, nullable=True)
    match_type = Column(String(30), nullable=False, default="CONTAINS_ANY")  # EXACT_MATCH, CONTAINS_ANY, CONTAINS_ALL, ANY_COMMENT
    trigger_keywords = Column(Text, nullable=False, default="[]")  # JSON encoded list of strings
    dm_message_template = Column(Text, nullable=False)
    reply_comment_template = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    cooldown_minutes = Column(Integer, nullable=False, default=60)
    total_triggered_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="automations")
    instagram_account = relationship("InstagramAccount", back_populates="automations")
    logs = relationship("AutomationLog", back_populates="automation", cascade="all, delete-orphan")

class AutomationLog(Base):
    __tablename__ = "automation_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    automation_id = Column(String(36), ForeignKey("automations.id"), nullable=False, index=True)
    recipient_ig_id = Column(String(64), nullable=False)
    recipient_username = Column(String(100), nullable=False)
    trigger_comment_id = Column(String(64), nullable=True)
    trigger_comment_text = Column(Text, nullable=True)
    dm_text_sent = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="SUCCESS")  # SUCCESS, PENDING, RATE_LIMITED, FAILED, SIMULATED
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    automation = relationship("Automation", back_populates="logs")
