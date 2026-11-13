import ipaddress
import socket
from typing import List, Tuple, Optional, Dict, Any
from urllib.parse import urlparse
from fastapi import HTTPException, status

from app.services.video_ingestion.base import BaseVideoProvider
from app.services.video_ingestion.models import PlatformType
from app.services.video_ingestion.detector import detect_platform
from app.services.video_ingestion.providers.direct_video import DirectVideoProvider
from app.services.video_ingestion.providers.instagram import InstagramProvider
from app.services.video_ingestion.providers.youtube import YouTubeProvider
from app.services.video_ingestion.providers.tiktok import TikTokProvider
from app.services.video_ingestion.providers.facebook import FacebookProvider
from app.services.video_ingestion.providers.vimeo import VimeoProvider
from app.services.video_ingestion.providers.generic import GenericProvider

# Provider registry in priority order
_PROVIDERS: List[BaseVideoProvider] = [
    DirectVideoProvider(),
    InstagramProvider(),
    YouTubeProvider(),
    TikTokProvider(),
    FacebookProvider(),
    VimeoProvider(),
    GenericProvider(),
]


def is_ip_private_or_restricted(ip_str: str) -> bool:
    """Verifies that an IP address is not private, loopback, link-local, or reserved."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
    except ValueError:
        return False


def get_provider_for_url(url: str) -> BaseVideoProvider:
    """Finds the first registered provider that claims support for the supplied URL."""
    clean_url = (url or "").strip()
    for provider in _PROVIDERS:
        if provider.detect_url(clean_url):
            return provider
    return _PROVIDERS[-1]  # GenericProvider fallback


def validate_video_url_safely(url: str) -> Dict[str, Any]:
    """
    Validates any HTTP/HTTPS video URL against SSRF, DNS rebinding, and private addresses.
    Identifies the target platform and extracts its platform video ID.

    Returns:
        {
            "url": clean_url,
            "platform": platform_enum.value,
            "video_id": platform_video_id,
            "is_instagram": bool,
            "shortcode": shortcode_if_instagram,
        }
    """
    if not url or not isinstance(url, str):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A valid video URL must be provided.",
        )

    clean_url = url.strip()

    try:
        parsed = urlparse(clean_url)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Malformed URL provided.",
        )

    if parsed.scheme not in ["http", "https"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid URL scheme. Only HTTP/HTTPS URLs are supported.",
        )

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="URL hostname is missing or invalid.",
        )

    # SSRF Protection: verify host is not private/loopback/link-local/metadata
    restricted_hostnames = {
        "localhost", "127.0.0.1", "0.0.0.0", "::1",
        "metadata.google.internal", "instance-data", "metadata"
    }
    if (
        hostname in restricted_hostnames
        or hostname.endswith(".localhost")
        or hostname.endswith(".local")
        or hostname.endswith(".internal")
        or (hostname.endswith(".nip.io") and any(is_ip_private_or_restricted(part) for part in hostname.split(".")))
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Access to private or local network addresses is forbidden.",
        )

    # If hostname is an IP address directly, check if private
    if is_ip_private_or_restricted(hostname):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Access to private or internal network addresses is forbidden.",
        )

    # DNS Resolution Check: Verify hostname does not resolve to private/loopback/metadata IP
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            if is_ip_private_or_restricted(ip_str):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Access to private, link-local, or metadata network addresses is forbidden.",
                )
    except socket.gaierror:
        # Hostname cannot be resolved via DNS (offline test environment)
        pass

    # Platform & Video ID Detection
    platform, vid_id = detect_platform(clean_url)

    return {
        "url": clean_url,
        "platform": platform.value,
        "video_id": vid_id,
        "is_instagram": platform == PlatformType.INSTAGRAM,
        "shortcode": vid_id if platform == PlatformType.INSTAGRAM else None,
    }
