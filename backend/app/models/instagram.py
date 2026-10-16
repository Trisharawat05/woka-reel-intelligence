import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class InstagramAccount(Base):
    __tablename__ = "instagram_accounts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    ig_user_id = Column(String(64), nullable=False, index=True)
    username = Column(String(100), nullable=False, index=True)
    name = Column(String(120), nullable=True)
    profile_pic_url = Column(Text, nullable=True)
    encrypted_access_token = Column(Text, nullable=False)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    is_connected = Column(Boolean, nullable=False, default=True)
    is_sandbox = Column(Boolean, nullable=False, default=False)
    followers_count = Column(Integer, nullable=False, default=0)
    media_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="instagram_accounts")
    automations = relationship("Automation", back_populates="instagram_account", cascade="all, delete-orphan")
