import re
from typing import Tuple, Optional
from urllib.parse import urlparse

from app.services.video_ingestion.models import PlatformType

_DIRECT_VIDEO_EXTENSIONS = (".mp4", ".mov", ".webm", ".m4v", ".avi", ".mkv")

_KNOWN_CDN_DOMAINS = (
    ".fbcdn.net",
    ".cdninstagram.com",
    ".fbsbx.com",
    ".fna.fbcdn.net",
    "r2.cloudflarestorage.com",
    "storage.googleapis.com",
)

IG_REGEX = re.compile(
    r"(?:https?:\/\/)?(?:www\.)?(?:instagram\.com|instagr\.am)\/(?:reel|p|tv)\/([a-zA-Z0-9_-]+)",
    re.IGNORECASE,
)

YOUTUBE_REGEX = re.compile(
    r"(?:https?:\/\/)?(?:www\.|m\.)?(?:youtube\.com\/(?:watch\?v=|shorts\/|embed\/|v\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})",
    re.IGNORECASE,
)

TIKTOK_REGEX = re.compile(
    r"(?:https?:\/\/)?(?:www\.|m\.)?tiktok\.com\/@[^\/]+\/video\/(\d+)|(?:https?:\/\/)?(?:vm|vt)\.tiktok\.com\/([a-zA-Z0-9_-]+)|(?:https?:\/\/)?(?:www\.)?tiktok\.com\/t\/([a-zA-Z0-9_-]+)",
    re.IGNORECASE,
)

FB_REGEX = re.compile(
    r"(?:https?:\/\/)?(?:www\.|m\.|web\.)?(?:facebook\.com\/(?:reel\/|watch\/\?v=|.+?\/videos\/)|fb\.watch\/)([a-zA-Z0-9_-]+)",
    re.IGNORECASE,
)

VIMEO_REGEX = re.compile(
    r"(?:https?:\/\/)?(?:www\.)?(?:vimeo\.com\/(?:channels\/(?:\w+\/)?|groups\/(?:[^\/]*)\/videos\/|album\/(?:\d+)\/video\/|video\/|)(\d+)|player\.vimeo\.com\/video\/(\d+))",
    re.IGNORECASE,
)


def is_direct_video_url(url: str) -> bool:
    """Detects whether a URL directly targets a raw video file or CDN media stream."""
    if not url:
        return False
    try:
        parsed = urlparse(url.strip())
        path_lower = (parsed.path or "").lower()
        clean_url_lower = url.strip().lower()

        # Check file extension in path or before query string
        if any(path_lower.endswith(ext) for ext in _DIRECT_VIDEO_EXTENSIONS):
            return True
        if any(clean_url_lower.split("?")[0].endswith(ext) for ext in _DIRECT_VIDEO_EXTENSIONS):
            return True

        # Check known video CDN host patterns
        hostname = (parsed.hostname or "").lower()
        if any(hostname.endswith(domain) or domain in hostname for domain in _KNOWN_CDN_DOMAINS):
            # Check that it's a media endpoint, not a main web portal
            if any(ext in path_lower for ext in (".mp4", ".mov", ".webm", "/v/", "/t50.", "/o1/")):
                return True
    except Exception:
        return False
    return False


def detect_platform(url: str) -> Tuple[PlatformType, Optional[str]]:
    """
    Identifies the video platform from the URL and extracts its platform video ID.

    Returns:
        (PlatformType, platform_video_id)
    """
    if not url or not isinstance(url, str):
        return PlatformType.OTHER, None

    clean_url = url.strip()

    # Priority 1: Check if it's a direct video link or CDN stream first
    if is_direct_video_url(clean_url):
        parsed = urlparse(clean_url)
        filename = (parsed.path.split("/")[-1] if parsed.path else "").split("?")[0]
        video_id = filename if filename and "." in filename else None
        return PlatformType.DIRECT_VIDEO, video_id

    # Priority 2: YouTube
    yt_match = YOUTUBE_REGEX.search(clean_url)
    if yt_match:
        video_id = yt_match.group(1)
        return PlatformType.YOUTUBE, video_id

    # Priority 3: Instagram
    ig_match = IG_REGEX.search(clean_url)
    if ig_match:
        shortcode = ig_match.group(1)
        return PlatformType.INSTAGRAM, shortcode

    # Priority 4: TikTok
    tt_match = TIKTOK_REGEX.search(clean_url)
    if tt_match:
        video_id = tt_match.group(1) or tt_match.group(2) or tt_match.group(3)
        return PlatformType.TIKTOK, video_id

    # Priority 5: Facebook
    fb_match = FB_REGEX.search(clean_url)
    if fb_match:
        video_id = fb_match.group(1)
        return PlatformType.FACEBOOK, video_id

    # Priority 6: Vimeo
    vm_match = VIMEO_REGEX.search(clean_url)
    if vm_match:
        video_id = vm_match.group(1) or vm_match.group(2)
        return PlatformType.VIMEO, video_id

    # Priority 7: Generic / Other
    return PlatformType.OTHER, None
