import os
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
from app.services.video_ingestion.detector import is_direct_video_url
from app.services.video_intelligence.video_processor import (
    download_remote_video_with_diagnostics,
    _is_public_safe_video_url,
)


class DirectVideoProvider(BaseVideoProvider):
    name = "direct_video"
    platform = PlatformType.DIRECT_VIDEO

    def detect_url(self, url: str) -> bool:
        return is_direct_video_url(url)

    def extract_video_id(self, url: str) -> Optional[str]:
        try:
            parsed = urlparse(url.strip())
            filename = (parsed.path.split("/")[-1] if parsed.path else "").split("?")[0]
            return filename if filename and "." in filename else None
        except Exception:
            return None

    def validate_access(self, url: str) -> AccessValidationResult:
        if not _is_public_safe_video_url(url):
            return AccessValidationResult(
                allowed=False,
                status=RetrievalStatus.EXTRACTION_FAILED,
                reason="URL failed security validation (private/internal IP address or restricted domain).",
                next_action="NONE",
            )
        return AccessValidationResult(
            allowed=True,
            status=RetrievalStatus.DOWNLOADING_VIDEO,
            reason="Publicly routable direct video resource.",
            next_action="NONE",
        )

    def extract_metadata(self, url: str) -> VideoMetadata:
        vid_id = self.extract_video_id(url)
        title = f"Direct Video — {vid_id}" if vid_id else "Direct Video Stream"
        return VideoMetadata(
            platform=PlatformType.DIRECT_VIDEO,
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
                video_source="BLOCKED",
                retrieval_status=val.status,
                limitation_reason=val.reason,
                metadata=meta,
                next_action=val.next_action,
            )

        tmp_path, video_source, limitation_reason = download_remote_video_with_diagnostics(url)

        if tmp_path and os.path.exists(tmp_path):
            return ExtractionResult(
                video_path=tmp_path,
                video_source="DIRECT_VIDEO",
                retrieval_status=RetrievalStatus.VIDEO_RETRIEVED,
                limitation_reason=None,
                metadata=meta,
                next_action="NONE",
            )

        if video_source == "HTTP_AUTH_REQUIRED":
            return ExtractionResult(
                video_path=None,
                video_source=video_source,
                retrieval_status=RetrievalStatus.AUTH_REQUIRED,
                limitation_reason=limitation_reason or "Direct video stream requires authentication or presigned link expired.",
                metadata=meta,
                next_action="LOGIN",
            )

        return ExtractionResult(
            video_path=None,
            video_source=video_source or "EXTRACTION_FAILED",
            retrieval_status=RetrievalStatus.EXTRACTION_FAILED,
            limitation_reason=limitation_reason or "Failed to download remote video stream.",
            metadata=meta,
            next_action="UPLOAD_MP4",
            next_action_url="#upload",
        )
