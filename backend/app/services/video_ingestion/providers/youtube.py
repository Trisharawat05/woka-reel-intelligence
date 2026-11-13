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
from app.services.video_ingestion.detector import YOUTUBE_REGEX

logger = logging.getLogger(__name__)


class YouTubeProvider(BaseVideoProvider):
    name = "youtube"
    platform = PlatformType.YOUTUBE

    def detect_url(self, url: str) -> bool:
        if not url:
            return False
        parsed = urlparse(url.strip())
        hostname = (parsed.hostname or "").lower()
        return "youtube.com" in hostname or hostname == "youtu.be" or hostname.endswith(".youtube.com")

    def extract_video_id(self, url: str) -> Optional[str]:
        match = YOUTUBE_REGEX.search(url)
        return match.group(1) if match else None

    def validate_access(self, url: str) -> AccessValidationResult:
        return AccessValidationResult(
            allowed=False,
            status=RetrievalStatus.UNSUPPORTED,
            reason=(
                "YouTube watch pages and Shorts do not provide raw MP4 video streams without platform client execution "
                "or Google API authorization. To analyze this video's visual pacing, cuts, and safe zones, please upload "
                "the video file directly (Mode B)."
            ),
            next_action="UPLOAD_MP4",
            next_action_url="#upload",
        )

    def extract_metadata(self, url: str) -> VideoMetadata:
        vid_id = self.extract_video_id(url)
        default_title = f"YouTube Video — {vid_id}" if vid_id else "YouTube Video"
        thumbnail_url = f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg" if vid_id else None

        title = default_title
        author = None
        raw_payload = None

        if vid_id:
            try:
                # Query YouTube official public oEmbed endpoint
                oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid_id}&format=json"
                with httpx.Client(timeout=3.0, follow_redirects=True) as client:
                    resp = client.get(oembed_url)
                    if resp.status_code == 200:
                        data = resp.json()
                        title = data.get("title") or default_title
                        author = data.get("author_name")
                        thumbnail_url = data.get("thumbnail_url") or thumbnail_url
                        raw_payload = data
            except Exception as e:
                logger.debug("YouTube oEmbed lookup skipped: %s", e)

        return VideoMetadata(
            platform=PlatformType.YOUTUBE,
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
            video_source="YOUTUBE_UNSUPPORTED",
            retrieval_status=val.status,
            limitation_reason=val.reason,
            metadata=meta,
            next_action=val.next_action,
            next_action_url=val.next_action_url,
        )
