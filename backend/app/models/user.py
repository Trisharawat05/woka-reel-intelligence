import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(120), nullable=False)
    role = Column(String(20), nullable=False, default="CREATOR")  # CREATOR, BRAND, AGENCY, ADMIN
    avatar_url = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    owned_workspaces = relationship("Workspace", back_populates="owner", cascade="all, delete-orphan")
    memberships = relationship("WorkspaceMember", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(120), nullable=False)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    owner = relationship("User", back_populates="owned_workspaces")
    members = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")
    instagram_accounts = relationship("InstagramAccount", back_populates="workspace", cascade="all, delete-orphan")
    automations = relationship("Automation", back_populates="workspace", cascade="all, delete-orphan")
    analytics_snapshots = relationship("CreatorAnalytics", back_populates="workspace", cascade="all, delete-orphan")
    creator_profile = relationship("CreatorProfile", back_populates="workspace", uselist=False, cascade="all, delete-orphan")
    brand_campaigns = relationship("BrandCampaign", back_populates="brand_workspace", cascade="all, delete-orphan")
    campaign_applications = relationship("CampaignApplication", back_populates="creator_workspace", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="workspace", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="workspace", uselist=False, cascade="all, delete-orphan")

class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    role_in_workspace = Column(String(20), default="MEMBER", nullable=False)  # OWNER, ADMIN, MEMBER
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="memberships")

class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    jti = Column(String(64), unique=True, index=True, nullable=False)
    token_type = Column(String(20), nullable=False, default="access")  # access or refresh
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class UsedOAuthNonce(Base):
    __tablename__ = "used_oauth_nonces"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    nonce = Column(String(64), unique=True, index=True, nullable=False)
    workspace_id = Column(String(36), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


