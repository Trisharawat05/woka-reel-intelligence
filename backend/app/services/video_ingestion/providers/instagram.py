import html
import json
import logging
import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import httpx

from app.config import settings
from app.services.video_ingestion.base import BaseVideoProvider
from app.services.video_ingestion.models import (
    PlatformType,
    RetrievalStatus,
    AccessValidationResult,
    VideoMetadata,
    ExtractionResult,
)
from app.services.video_ingestion.detector import IG_REGEX, is_direct_video_url
from app.services.video_intelligence.video_processor import (
    download_remote_video_with_diagnostics,
    _resolve_and_check_ssrf,
)

logger = logging.getLogger(__name__)


def parse_metric_num(s: str) -> Optional[int]:
    """Parses numeric string representations including commas, decimals, and k/m multipliers."""
    if not s:
        return None
    cleaned = str(s).strip().replace(",", "")
    match = re.match(r"^([\d.]+)\s*([kKmMbB]?)$", cleaned)
    if not match:
        return None
    val = float(match.group(1))
    unit = match.group(2).lower()
    if unit == "k":
        val *= 1_000
    elif unit == "m":
        val *= 1_000_000
    elif unit == "b":
        val *= 1_000_000_000
    return int(round(val))


def extract_meta_tag(html_text: str, prop: str) -> Optional[str]:
    """Extracts content attribute from <meta> tag by property or name."""
    patterns = [
        rf'<meta\s+[^>]*?(?:property|name)=["\']{re.escape(prop)}["\'][^>]*?content=["\'](.*?)["\']',
        rf'<meta\s+[^>]*?content=["\'](.*?)["\'][^>]*?(?:property|name)=["\']{re.escape(prop)}["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html_text, re.IGNORECASE | re.DOTALL)
        if match:
            return html.unescape(match.group(1).strip())
    return None


def extract_from_json_ld(obj: Any) -> Dict[str, Any]:
    res: Dict[str, Any] = {}
    if isinstance(obj, list):
        for item in obj:
            res.update(extract_from_json_ld(item))
        return res
    if not isinstance(obj, dict):
        return res

    obj_type = obj.get("@type")
    if obj_type in ("VideoObject", "ImageObject", "SocialMediaPosting"):
        if obj.get("name"):
            res["title"] = str(obj["name"]).strip()
        if obj.get("description"):
            res["caption"] = str(obj["description"]).strip()
        if obj.get("thumbnailUrl"):
            res["thumbnail_url"] = str(obj["thumbnailUrl"]).strip()
        if isinstance(obj.get("author"), dict) and obj["author"].get("name"):
            res["author"] = str(obj["author"]["name"]).strip()
        elif isinstance(obj.get("author"), str):
            res["author"] = str(obj["author"]).strip()

        # Interaction statistics (likes, comments, views)
        interactions = obj.get("interactionStatistic") or []
        if isinstance(interactions, dict):
            interactions = [interactions]
        for stat in interactions:
            if not isinstance(stat, dict):
                continue
            itype = str(stat.get("interactionType", ""))
            cnt = stat.get("userInteractionCount")
            if cnt is not None:
                try:
                    num_cnt = int(cnt)
                    if "LikeAction" in itype:
                        res["likes"] = num_cnt
                    elif "CommentAction" in itype:
                        res["comments"] = num_cnt
                    elif "WatchAction" in itype or "ViewAction" in itype:
                        res["views"] = num_cnt
                except (ValueError, TypeError):
                    pass

        if obj.get("duration"):
            dur_m = re.search(r"PT(?:(\d+)M)?(?:(\d+)S)?", str(obj["duration"]))
            if dur_m:
                mins = int(dur_m.group(1) or 0)
                secs = int(dur_m.group(2) or 0)
                res["duration_seconds"] = float(mins * 60 + secs)

    return res


class InstagramProvider(BaseVideoProvider):
    name = "instagram"
    platform = PlatformType.INSTAGRAM

    def detect_url(self, url: str) -> bool:
        if not url:
            return False
        parsed = urlparse(url.strip())
        hostname = (parsed.hostname or "").lower()
        return "instagram.com" in hostname or hostname == "instagr.am" or hostname.endswith(".instagram.com")

    def extract_video_id(self, url: str) -> Optional[str]:
        match = IG_REGEX.search(url)
        return match.group(1) if match else None

    def validate_access(self, url: str) -> AccessValidationResult:
        if is_direct_video_url(url):
            return AccessValidationResult(
                allowed=True,
                status=RetrievalStatus.DOWNLOADING_VIDEO,
                reason="Direct Instagram CDN media stream URL detected.",
                next_action="NONE",
            )

        # Webpage URL (instagram.com/reel/...)
        return AccessValidationResult(
            allowed=False,
            status=RetrievalStatus.CONNECT_ACCOUNT,
            reason=(
                "Instagram Reel webpage URLs require authenticated access via Meta Graph API to retrieve raw video streams. "
                "Please connect your Instagram professional account (Mode C) or upload the video file directly (Mode B)."
            ),
            next_action="CONNECT_INSTAGRAM",
            next_action_url="/dashboard/instagram",
        )

    def _fetch_meta_oembed(self, canonical_url: str) -> Optional[Dict[str, Any]]:
        """Queries Meta's official oEmbed endpoint if credentials or public query is supported."""
        app_id = getattr(settings, "META_APP_ID", None)
        app_secret = getattr(settings, "META_APP_SECRET", None) or getattr(settings, "META_CLIENT_SECRET", None)
        
        params = {"url": canonical_url}
        if app_id and app_secret:
            params["access_token"] = f"{app_id}|{app_secret}"

        oembed_url = "https://graph.facebook.com/v19.0/instagram_oembed"
        try:
            with httpx.Client(timeout=3.5, follow_redirects=True) as client:
                resp = client.get(oembed_url, params=params)
                if resp.status_code == 200:
                    return resp.json()
                logger.debug("Meta oEmbed returned HTTP %s for %s", resp.status_code, canonical_url)
        except Exception as e:
            logger.debug("Meta oEmbed query skipped or error: %s", e)
        return None

    def _fetch_public_page_metadata(self, canonical_url: str) -> Optional[Dict[str, Any]]:
        """Fetches public HTML metadata (OpenGraph & JSON-LD) with strict SSRF protection."""
        parsed = urlparse(canonical_url)
        if not parsed.hostname or not _resolve_and_check_ssrf(parsed.hostname):
            logger.warning("SSRF blocked or unresolvable hostname for public page metadata: %s", parsed.hostname)
            return None

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            with httpx.Client(timeout=3.5, follow_redirects=True, headers=headers) as client:
                resp = client.get(canonical_url)
                if resp.status_code != 200:
                    logger.debug("Public page fetch returned HTTP %s for %s", resp.status_code, canonical_url)
                    return None

                html_text = resp.text
                meta_res: Dict[str, Any] = {}

                # 1. Parse OpenGraph and meta tags
                og_title = extract_meta_tag(html_text, "og:title")
                og_desc = extract_meta_tag(html_text, "og:description")
                og_image = extract_meta_tag(html_text, "og:image")

                if og_image:
                    meta_res["thumbnail_url"] = og_image

                if og_title:
                    m_author = re.search(r"^([A-Za-z0-9_.-]+)\s+on\s+Instagram", og_title)
                    if m_author:
                        meta_res["author"] = m_author.group(1).strip()
                    m_title_caption = re.search(r'[:]\s*["“](.+)["”]?$', og_title)
                    if m_title_caption:
                        meta_res["caption"] = m_title_caption.group(1).strip().rstrip('"”')
                        meta_res["title"] = meta_res["caption"].split("\n")[0][:70]

                if og_desc:
                    m_likes = re.search(r'([\d,.]+[kKmMbB]?)\s+likes?', og_desc, re.IGNORECASE)
                    if m_likes:
                        meta_res["likes"] = parse_metric_num(m_likes.group(1))

                    m_comments = re.search(r'([\d,.]+[kKmMbB]?)\s+comments?', og_desc, re.IGNORECASE)
                    if m_comments:
                        meta_res["comments"] = parse_metric_num(m_comments.group(1))

                    m_views = re.search(r'([\d,.]+[kKmMbB]?)\s+views?', og_desc, re.IGNORECASE)
                    if m_views:
                        meta_res["views"] = parse_metric_num(m_views.group(1))

                    m_desc_author = re.search(r'-\s+([A-Za-z0-9_.-]+)\s+on\s+', og_desc)
                    if m_desc_author and "author" not in meta_res:
                        meta_res["author"] = m_desc_author.group(1).strip()

                    m_desc_caption = re.search(r'[:]\s*["“](.+)["”]?$', og_desc)
                    if m_desc_caption and "caption" not in meta_res:
                        meta_res["caption"] = m_desc_caption.group(1).strip().rstrip('"”')
                        if "title" not in meta_res:
                            meta_res["title"] = meta_res["caption"].split("\n")[0][:70]

                # 2. Parse JSON-LD scripts
                json_ld_matches = re.findall(
                    r'<script\s+[^>]*?type=["\']application/ld\+json["\'][^>]*?>(.*?)</script>',
                    html_text,
                    re.IGNORECASE | re.DOTALL,
                )
                for script_content in json_ld_matches:
                    try:
                        data = json.loads(script_content.strip())
                        ld_res = extract_from_json_ld(data)
                        for k, v in ld_res.items():
                            if v is not None and (k not in meta_res or meta_res[k] is None):
                                meta_res[k] = v
                    except Exception:
                        pass

                return meta_res if meta_res else None
        except Exception as e:
            logger.debug("Public page metadata extraction failed for %s: %s", canonical_url, e)
            return None

    def extract_metadata(self, url: str) -> VideoMetadata:
        shortcode = self.extract_video_id(url)
        canonical_url = f"https://www.instagram.com/reel/{shortcode}/" if shortcode else url
        default_title = f"Instagram Reel — {shortcode}" if shortcode else "Instagram Video"

        title = default_title
        caption: Optional[str] = None
        author: Optional[str] = None
        thumbnail_url: Optional[str] = None
        duration_seconds: Optional[float] = None
        width: Optional[int] = None
        height: Optional[int] = None
        views: Optional[int] = None
        likes: Optional[int] = None
        comments: Optional[int] = None
        raw_payload: Dict[str, Any] = {}

        # 1. Attempt official Meta oEmbed lookup
        oembed_data = self._fetch_meta_oembed(canonical_url)
        if oembed_data:
            raw_payload["oembed"] = oembed_data
            if oembed_data.get("title"):
                caption = oembed_data["title"]
                first_line = caption.split("\n")[0].strip()
                if first_line:
                    title = first_line[:70]
            if oembed_data.get("author_name"):
                author = oembed_data["author_name"]
            if oembed_data.get("thumbnail_url"):
                thumbnail_url = oembed_data["thumbnail_url"]
            if oembed_data.get("width"):
                try:
                    width = int(oembed_data["width"])
                except (ValueError, TypeError):
                    pass
            if oembed_data.get("height"):
                try:
                    height = int(oembed_data["height"])
                except (ValueError, TypeError):
                    pass

        # 2. Attempt public HTML OpenGraph and JSON-LD lookup
        og_data = self._fetch_public_page_metadata(canonical_url)
        if og_data:
            raw_payload["opengraph"] = og_data
            if not caption and og_data.get("caption"):
                caption = og_data["caption"]
                first_line = caption.split("\n")[0].strip()
                if first_line:
                    title = first_line[:70]
            elif og_data.get("title") and title == default_title:
                title = og_data["title"]

            if not author and og_data.get("author"):
                author = og_data["author"]
            if not thumbnail_url and og_data.get("thumbnail_url"):
                thumbnail_url = og_data["thumbnail_url"]
            if og_data.get("likes") is not None:
                likes = og_data["likes"]
            if og_data.get("comments") is not None:
                comments = og_data["comments"]
            if og_data.get("views") is not None:
                views = og_data["views"]
            if og_data.get("duration_seconds") is not None:
                duration_seconds = og_data["duration_seconds"]

        return VideoMetadata(
            platform=PlatformType.INSTAGRAM,
            video_id=shortcode,
            title=title,
            caption=caption,
            author=author,
            thumbnail_url=thumbnail_url,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            views=views,
            likes=likes,
            comments=comments,
            raw_payload=raw_payload if raw_payload else None,
        )

    def retrieve_video(self, url: str) -> ExtractionResult:
        meta = self.extract_metadata(url)
        val = self.validate_access(url)

        if not val.allowed:
            return ExtractionResult(
                video_path=None,
                video_source="INSTAGRAM_WEBPAGE",
                retrieval_status=val.status,
                limitation_reason=val.reason,
                metadata=meta,
                next_action=val.next_action,
                next_action_url=val.next_action_url,
            )

        # Direct CDN stream
        tmp_path, video_source, limitation_reason = download_remote_video_with_diagnostics(url)
        if tmp_path:
            return ExtractionResult(
                video_path=tmp_path,
                video_source="INSTAGRAM_CDN",
                retrieval_status=RetrievalStatus.VIDEO_RETRIEVED,
                limitation_reason=None,
                metadata=meta,
                next_action="NONE",
            )

        return ExtractionResult(
            video_path=None,
            video_source=video_source or "EXTRACTION_FAILED",
            retrieval_status=RetrievalStatus.EXTRACTION_FAILED,
            limitation_reason=limitation_reason or "Failed to download Instagram CDN stream.",
            metadata=meta,
            next_action="CONNECT_INSTAGRAM",
            next_action_url="/dashboard/instagram",
        )
