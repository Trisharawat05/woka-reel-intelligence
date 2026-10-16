import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class ReelMediaAsset(Base):
    __tablename__ = "reel_media_assets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    storage_path = Column(Text, nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=False, default=0)
    mime_type = Column(String(100), nullable=False, default="video/mp4")
    duration_seconds = Column(Float, nullable=False, default=0.0)
    resolution_width = Column(Integer, nullable=False, default=0)
    resolution_height = Column(Integer, nullable=False, default=0)
    aspect_ratio = Column(String(20), nullable=False, default="9:16")
    fps = Column(Float, nullable=False, default=30.0)
    thumbnail_path = Column(Text, nullable=True)
    is_temporary = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    workspace = relationship("Workspace")


class ReelAnalysisJob(Base):
    __tablename__ = "reel_analysis_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    analysis_mode = Column(String(40), nullable=False)  # PUBLIC_URL, VIDEO_UPLOAD, CONNECTED_ACCOUNT
    input_type = Column(String(30), nullable=False)      # url, upload, connected_account
    status = Column(String(30), nullable=False, default="QUEUED")  # QUEUED, INGESTING, PROCESSING_VIDEO, ANALYZING_METRICS, GENERATING_AI_REPORT, COMPLETED, FAILED
    progress_percent = Column(Integer, nullable=False, default=0)
    stage_message = Column(String(255), nullable=False, default="Queued for analysis")
    error_message = Column(Text, nullable=True)
    source_url = Column(Text, nullable=True)
    source_media_id = Column(String(100), nullable=True)
    
    video_asset_id = Column(String(36), ForeignKey("reel_media_assets.id", ondelete="SET NULL"), nullable=True)
    report_id = Column(String(36), ForeignKey("reel_reports.id", ondelete="SET NULL", use_alter=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    workspace = relationship("Workspace")
    video_asset = relationship("ReelMediaAsset", foreign_keys=[video_asset_id])
    report = relationship("ReelReport", foreign_keys=[report_id], post_update=True)
    snapshots = relationship("ReelMetricSnapshot", back_populates="job", cascade="all, delete-orphan")


class ReelMetricSnapshot(Base):
    __tablename__ = "reel_metric_snapshots"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    job_id = Column(String(36), ForeignKey("reel_analysis_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    views_count = Column(Integer, nullable=False, default=0)
    reach_count = Column(Integer, nullable=False, default=0)
    impressions_count = Column(Integer, nullable=False, default=0)
    likes_count = Column(Integer, nullable=False, default=0)
    comments_count = Column(Integer, nullable=False, default=0)
    shares_count = Column(Integer, nullable=False, default=0)
    saves_count = Column(Integer, nullable=False, default=0)
    avg_watch_time_seconds = Column(Float, nullable=True)
    total_watch_time_seconds = Column(Float, nullable=True)
    reposts_count = Column(Integer, nullable=True)
    follows_attributed = Column(Integer, nullable=True)
    profile_activity = Column(Integer, nullable=True)
    
    source_type = Column(String(50), nullable=False, default="PUBLIC_SCRAPE_FALLBACK")  # META_GRAPH_API, PUBLIC_SCRAPE_FALLBACK, USER_DECLARED, SANDBOX_SIMULATED
    data_completeness = Column(Float, nullable=False, default=1.0)
    limitations_notes = Column(Text, nullable=True)

    workspace = relationship("Workspace")
    job = relationship("ReelAnalysisJob", back_populates="snapshots")


class ReelReport(Base):
    __tablename__ = "reel_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    job_id = Column(String(36), ForeignKey("reel_analysis_jobs.id", ondelete="CASCADE"), nullable=False, unique=True)
    title = Column(String(255), nullable=False, default="Instagram Reel Analysis")
    caption = Column(Text, nullable=True)
    analysis_mode = Column(String(40), nullable=False)  # PUBLIC_URL, VIDEO_UPLOAD, CONNECTED_ACCOUNT
    thumbnail_url = Column(Text, nullable=True)
    duration_seconds = Column(Float, nullable=False, default=0.0)

    # 4 Core Scores (0 - 100)
    creative_quality_score = Column(Float, nullable=False, default=0.0)
    performance_score = Column(Float, nullable=False, default=0.0)
    growth_conversion_score = Column(Float, nullable=False, default=0.0)
    viral_potential_estimate = Column(Float, nullable=False, default=0.0)

    # Detailed JSON documents
    score_breakdown_json = Column(Text, nullable=False, default="{}")
    calculated_metrics_json = Column(Text, nullable=False, default="{}")
    video_intelligence_json = Column(Text, nullable=False, default="{}")
    timeline_findings_json = Column(Text, nullable=False, default="[]")
    prioritized_action_plan_json = Column(Text, nullable=False, default="{}")
    creative_alternatives_json = Column(Text, nullable=False, default="{}")
    provenance_json = Column(Text, nullable=False, default="{}")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    workspace = relationship("Workspace")


class ReelComparison(Base):
    __tablename__ = "reel_comparisons"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    report_ids = Column(Text, nullable=False)  # JSON array of report IDs
    comparison_summary_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    workspace = relationship("Workspace")
