import logging
from typing import Optional
from urllib.parse import urlparse
import httpx

from app.services.video_ingestion.base import BaseVideoProvider
from app.services.video_ingestion.models import (
    PlatformType,
    RetrievalStatus,
    AccessValidationResult,
    VideoMetadata,
    ExtractionResult,
)
from app.services.video_ingestion.detector import VIMEO_REGEX, is_direct_video_url
from app.services.video_intelligence.video_processor import download_remote_video_with_diagnostics

logger = logging.getLogger(__name__)


class VimeoProvider(BaseVideoProvider):
    name = "vimeo"
    platform = PlatformType.VIMEO

    def detect_url(self, url: str) -> bool:
        if not url:
            return False
        parsed = urlparse(url.strip())
        hostname = (parsed.hostname or "").lower()
        return "vimeo.com" in hostname or hostname.endswith(".vimeo.com")

    def extract_video_id(self, url: str) -> Optional[str]:
        match = VIMEO_REGEX.search(url)
        if match:
            return match.group(1) or match.group(2)
        return None

    def validate_access(self, url: str) -> AccessValidationResult:
        if is_direct_video_url(url):
            return AccessValidationResult(
                allowed=True,
                status=RetrievalStatus.DOWNLOADING_VIDEO,
                reason="Direct Vimeo video file URL detected.",
                next_action="NONE",
            )

        return AccessValidationResult(
            allowed=False,
            status=RetrievalStatus.UNSUPPORTED,
            reason=(
                "Standard Vimeo watch pages require Vimeo Pro API access or direct video links to download raw video streams. "
                "Please upload the video file directly (Mode B) or provide a direct video link."
            ),
            next_action="UPLOAD_MP4",
            next_action_url="#upload",
        )

    def extract_metadata(self, url: str) -> VideoMetadata:
        vid_id = self.extract_video_id(url)
        default_title = f"Vimeo Video — {vid_id}" if vid_id else "Vimeo Video"

        title = default_title
        author = None
        thumbnail_url = None
        duration = None
        caption = None
        raw_payload = None

        if vid_id:
            try:
                oembed_url = f"https://vimeo.com/api/oembed.json?url=https://vimeo.com/{vid_id}"
                with httpx.Client(timeout=3.0, follow_redirects=True) as client:
                    resp = client.get(oembed_url)
                    if resp.status_code == 200:
                        data = resp.json()
                        title = data.get("title") or default_title
                        author = data.get("author_name")
                        thumbnail_url = data.get("thumbnail_url")
                        duration = data.get("duration")
                        caption = data.get("description")
                        raw_payload = data
            except Exception as e:
                logger.debug("Vimeo oEmbed lookup skipped: %s", e)

        return VideoMetadata(
            platform=PlatformType.VIMEO,
            video_id=vid_id,
            title=title,
            caption=caption,
            author=author,
            thumbnail_url=thumbnail_url,
            duration_seconds=float(duration) if duration else None,
            raw_payload=raw_payload,
        )

    def retrieve_video(self, url: str) -> ExtractionResult:
        meta = self.extract_metadata(url)
        val = self.validate_access(url)

        if not val.allowed:
            return ExtractionResult(
                video_path=None,
                video_source="VIMEO_WEBPAGE",
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
                video_source="VIMEO_DIRECT",
                retrieval_status=RetrievalStatus.VIDEO_RETRIEVED,
                limitation_reason=None,
                metadata=meta,
                next_action="NONE",
            )

        return ExtractionResult(
            video_path=None,
            video_source=video_source or "EXTRACTION_FAILED",
            retrieval_status=RetrievalStatus.EXTRACTION_FAILED,
            limitation_reason=limitation_reason or "Failed to download Vimeo video stream.",
            metadata=meta,
            next_action="UPLOAD_MP4",
            next_action_url="#upload",
        )
