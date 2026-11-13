from typing import Optional
from urllib.parse import urlparse

from app.services.video_ingestion.base import BaseVideoProvider
from app.services.video_ingestion.models import (
    PlatformType,
    RetrievalStatus,
    AccessValidationResult,
    VideoMetadata,
    ExtractionResult,
)
from app.services.video_ingestion.detector import FB_REGEX, is_direct_video_url
from app.services.video_intelligence.video_processor import download_remote_video_with_diagnostics


class FacebookProvider(BaseVideoProvider):
    name = "facebook"
    platform = PlatformType.FACEBOOK

    def detect_url(self, url: str) -> bool:
        if not url:
            return False
        parsed = urlparse(url.strip())
        hostname = (parsed.hostname or "").lower()
        return "facebook.com" in hostname or hostname == "fb.watch" or hostname.endswith(".facebook.com")

    def extract_video_id(self, url: str) -> Optional[str]:
        match = FB_REGEX.search(url)
        return match.group(1) if match else None

    def validate_access(self, url: str) -> AccessValidationResult:
        if is_direct_video_url(url):
            return AccessValidationResult(
                allowed=True,
                status=RetrievalStatus.DOWNLOADING_VIDEO,
                reason="Direct Facebook CDN media stream URL detected.",
                next_action="NONE",
            )

        return AccessValidationResult(
            allowed=False,
            status=RetrievalStatus.CONNECT_ACCOUNT,
            reason=(
                "Facebook video and Reel webpage URLs require authentication to access raw video streams. "
                "Please connect your Meta account (Mode C) or upload the video file directly (Mode B)."
            ),
            next_action="CONNECT_INSTAGRAM",
            next_action_url="/dashboard/instagram",
        )

    def extract_metadata(self, url: str) -> VideoMetadata:
        vid_id = self.extract_video_id(url)
        title = f"Facebook Reel — {vid_id}" if vid_id else "Facebook Video"
        return VideoMetadata(
            platform=PlatformType.FACEBOOK,
            video_id=vid_id,
            title=title,
            caption=None,
            author=None,
            thumbnail_url=None,
        )

    def retrieve_video(self, url: str) -> ExtractionResult:
        meta = self.extract_metadata(url)
        val = self.validate_access(url)

        if not val.allowed:
            return ExtractionResult(
                video_path=None,
                video_source="FACEBOOK_WEBPAGE",
                retrieval_status=val.status,
                limitation_reason=val.reason,
                metadata=meta,
                next_action=val.next_action,
                next_action_url=val.next_action_url,
            )

        tmp_path, video_source, limitation_reason = download_remote_video_with_diagnostics(url)
        if tmp_path:
            return ExtractionResult(
                video_path=tmp_path,
                video_source="FACEBOOK_CDN",
                retrieval_status=RetrievalStatus.VIDEO_RETRIEVED,
                limitation_reason=None,
                metadata=meta,
                next_action="NONE",
            )

        return ExtractionResult(
            video_path=None,
            video_source=video_source or "EXTRACTION_FAILED",
            retrieval_status=RetrievalStatus.EXTRACTION_FAILED,
            limitation_reason=limitation_reason or "Failed to download Facebook media stream.",
            metadata=meta,
            next_action="CONNECT_INSTAGRAM",
            next_action_url="/dashboard/instagram",
        )
