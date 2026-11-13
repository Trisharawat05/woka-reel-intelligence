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
from app.services.video_ingestion.detector import TIKTOK_REGEX

logger = logging.getLogger(__name__)


class TikTokProvider(BaseVideoProvider):
    name = "tiktok"
    platform = PlatformType.TIKTOK

    def detect_url(self, url: str) -> bool:
        if not url:
            return False
        parsed = urlparse(url.strip())
        hostname = (parsed.hostname or "").lower()
        return "tiktok.com" in hostname or hostname.endswith(".tiktok.com")

    def extract_video_id(self, url: str) -> Optional[str]:
        match = TIKTOK_REGEX.search(url)
        if match:
            return match.group(1) or match.group(2) or match.group(3)
        return None

    def validate_access(self, url: str) -> AccessValidationResult:
        return AccessValidationResult(
            allowed=False,
            status=RetrievalStatus.UNSUPPORTED,
            reason=(
                "TikTok video pages do not expose direct raw MP4 video streams without platform authorization. "
                "To analyze this video's visual cuts, pacing, and safe zones, please upload the video file directly (Mode B)."
            ),
            next_action="UPLOAD_MP4",
            next_action_url="#upload",
        )

    def extract_metadata(self, url: str) -> VideoMetadata:
        vid_id = self.extract_video_id(url)
        default_title = f"TikTok Video — {vid_id}" if vid_id else "TikTok Video"

        title = default_title
        author = None
        thumbnail_url = None
        raw_payload = None

        try:
            oembed_url = f"https://www.tiktok.com/oembed?url={url.strip()}"
            with httpx.Client(timeout=3.0, follow_redirects=True) as client:
                resp = client.get(oembed_url)
                if resp.status_code == 200:
                    data = resp.json()
                    title = data.get("title") or default_title
                    author = data.get("author_name")
                    thumbnail_url = data.get("thumbnail_url")
                    raw_payload = data
        except Exception as e:
            logger.debug("TikTok oEmbed lookup skipped: %s", e)

        return VideoMetadata(
            platform=PlatformType.TIKTOK,
            video_id=vid_id,
            title=title,
            caption=None,
            author=author,
            thumbnail_url=thumbnail_url,
            raw_payload=raw_payload,
        )

    def retrieve_video(self, url: str) -> ExtractionResult:
        meta = self.extract_metadata(url)
        val = self.validate_access(url)

        return ExtractionResult(
            video_path=None,
            video_source="TIKTOK_UNSUPPORTED",
            retrieval_status=val.status,
            limitation_reason=val.reason,
            metadata=meta,
            next_action=val.next_action,
            next_action_url=val.next_action_url,
        )
