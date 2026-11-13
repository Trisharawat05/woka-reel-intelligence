from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from app.services.video_ingestion.models import (
    PlatformType,
    RetrievalStatus,
    AccessValidationResult,
    VideoMetadata,
    ExtractionResult,
)


class BaseVideoProvider(ABC):
    """
    Abstract base provider defining the pluggable extraction contract
    for each video platform and direct streaming mechanism.
    """

    name: str = "base"
    platform: PlatformType = PlatformType.OTHER

    @abstractmethod
    def detect_url(self, url: str) -> bool:
        """Returns True if this provider can handle the supplied URL."""
        pass

    @abstractmethod
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extracts platform-specific unique identifier (e.g. shortcode, video ID) if available."""
        pass

    @abstractmethod
    def validate_access(self, url: str) -> AccessValidationResult:
        """Determines if the video is accessible, requires authentication, or is unsupported."""
        pass

    @abstractmethod
    def extract_metadata(self, url: str) -> VideoMetadata:
        """Extracts available title, author, thumbnail, caption, and duration from official/permitted APIs."""
        pass

    @abstractmethod
    def retrieve_video(self, url: str) -> ExtractionResult:
        """
        Attempts to safely retrieve the raw video file.
        Returns ExtractionResult with local video path, status, and limitations.
        """
        pass

    def get_thumbnail(self, url: str) -> Optional[str]:
        """Convenience method to retrieve cover/thumbnail URL if available."""
        meta = self.extract_metadata(url)
        return meta.thumbnail_url

    def get_caption(self, url: str) -> Optional[str]:
        """Convenience method to retrieve caption/description text."""
        meta = self.extract_metadata(url)
        return meta.caption

    def get_engagement_metrics(self, url: str) -> Dict[str, Any]:
        """Extracts public engagement metrics if exposed officially."""
        meta = self.extract_metadata(url)
        return {
            "views": meta.views,
            "likes": meta.likes,
            "comments": meta.comments,
            "shares": meta.shares,
        }
