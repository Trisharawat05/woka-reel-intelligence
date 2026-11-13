from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class PlatformType(str, Enum):
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"
    VIMEO = "vimeo"
    DIRECT_VIDEO = "direct_video"
    OTHER = "other"


class RetrievalStatus(str, Enum):
    DETECTING_PLATFORM = "DETECTING_PLATFORM"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    CONNECT_ACCOUNT = "CONNECT_ACCOUNT"
    EXTRACTING_METADATA = "EXTRACTING_METADATA"
    DOWNLOADING_VIDEO = "DOWNLOADING_VIDEO"
    VIDEO_RETRIEVED = "VIDEO_RETRIEVED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    UNSUPPORTED = "UNSUPPORTED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"


class AccessValidationResult(BaseModel):
    allowed: bool
    status: RetrievalStatus
    reason: str
    next_action: Optional[str] = None  # e.g. "CONNECT_INSTAGRAM", "UPLOAD_MP4", "NONE"
    next_action_url: Optional[str] = None  # e.g. "/dashboard/instagram", "#upload"


class VideoMetadata(BaseModel):
    platform: PlatformType
    video_id: Optional[str] = None
    title: Optional[str] = None
    caption: Optional[str] = None
    author: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    raw_payload: Optional[Dict[str, Any]] = None


class ExtractionResult(BaseModel):
    video_path: Optional[str] = None  # Local filesystem path to downloaded temporary video file
    video_source: str  # e.g. "DIRECT_DOWNLOAD", "CDN_STREAM", "UNSUPPORTED", "AUTH_REQUIRED"
    retrieval_status: RetrievalStatus
    limitation_reason: Optional[str] = None
    metadata: VideoMetadata
    next_action: Optional[str] = None
    next_action_url: Optional[str] = None
