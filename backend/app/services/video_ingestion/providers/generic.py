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
from app.services.video_intelligence.video_processor import (
    download_remote_video_with_diagnostics,
    _is_public_safe_video_url,
)


class GenericProvider(BaseVideoProvider):
    name = "generic"
    platform = PlatformType.OTHER

    def detect_url(self, url: str) -> bool:
        return True  # Fallback provider matches any URL

    def extract_video_id(self, url: str) -> Optional[str]:
        try:
            parsed = urlparse(url.strip())
            segments = [s for s in parsed.path.split("/") if s]
            return segments[-1] if segments else parsed.hostname
        except Exception:
            return None

    def validate_access(self, url: str) -> AccessValidationResult:
        if not _is_public_safe_video_url(url):
            return AccessValidationResult(
                allowed=False,
                status=RetrievalStatus.EXTRACTION_FAILED,
                reason="URL points to a private, loopback, or restricted network address.",
                next_action="NONE",
            )
        return AccessValidationResult(
            allowed=True,
            status=RetrievalStatus.DOWNLOADING_VIDEO,
            reason="Publicly routable generic video resource.",
            next_action="NONE",
        )

    def extract_metadata(self, url: str) -> VideoMetadata:
        try:
            parsed = urlparse(url.strip())
            domain = parsed.hostname or "External"
        except Exception:
            domain = "External"

        return VideoMetadata(
            platform=PlatformType.OTHER,
            video_id=self.extract_video_id(url),
            title=f"Web Video ({domain})",
            caption=None,
            author=domain,
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
                next_action="NONE",
            )

        tmp_path, video_source, limitation_reason = download_remote_video_with_diagnostics(url)

        if tmp_path:
            return ExtractionResult(
                video_path=tmp_path,
                video_source="GENERIC_DOWNLOAD",
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
                limitation_reason=limitation_reason or "Video stream requires authentication.",
                metadata=meta,
                next_action="LOGIN",
            )

        if video_source == "HTML_RESPONSE_NOT_VIDEO":
            return ExtractionResult(
                video_path=None,
                video_source=video_source,
                retrieval_status=RetrievalStatus.UNSUPPORTED,
                limitation_reason=(
                    "The provided URL returned an HTML webpage instead of a raw video stream. "
                    "Webpage players do not expose raw video bytes publicly. "
                    "Please upload the video file directly (Mode B) or provide a direct video stream link."
                ),
                metadata=meta,
                next_action="UPLOAD_MP4",
                next_action_url="#upload",
            )

        return ExtractionResult(
            video_path=None,
            video_source=video_source or "EXTRACTION_FAILED",
            retrieval_status=RetrievalStatus.EXTRACTION_FAILED,
            limitation_reason=limitation_reason or "Could not retrieve video stream from this URL.",
            metadata=meta,
            next_action="UPLOAD_MP4",
            next_action_url="#upload",
        )
