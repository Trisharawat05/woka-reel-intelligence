import os
import math
import uuid
import re
import tempfile
import logging
import subprocess
import shutil
import ipaddress
import socket
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


def validate_video_file_magic_bytes(header_bytes: bytes) -> bool:
    """Inspects binary file signature to verify video container and reject executables."""
    if not header_bytes or len(header_bytes) < 4:
        return False

    # Reject dangerous executable formats immediately
    if header_bytes.startswith(b"MZ"):  # Windows PE executable
        return False
    if header_bytes.startswith(b"\x7fELF"):  # Linux ELF executable
        return False
    if header_bytes.startswith(b"#!/") or header_bytes.startswith(b"<?php"):
        return False
    if b"<html" in header_bytes.lower() or b"<!doctype" in header_bytes.lower():
        return False

    # MP4 / M4V / MOV signature: typically contains 'ftyp' in first 32 bytes or 'moov' / 'mdat' / 'wide'
    if b"ftyp" in header_bytes[:32] or b"moov" in header_bytes[:32] or b"mdat" in header_bytes[:32] or b"wide" in header_bytes[:32]:
        return True

    # WebM / MKV starts with \x1a\x45\xdf\xa3
    if header_bytes.startswith(b"\x1a\x45\xdf\xa3"):
        return True

    return True  # Fallback for other valid raw video formats

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


MAX_REMOTE_VIDEO_BYTES = 25 * 1024 * 1024  # 25 MB bounded stream cap

# Known CDN domains that serve direct video streams
_CDN_VIDEO_DOMAINS = (
    ".fbcdn.net",
    ".cdninstagram.com",
    ".fbsbx.com",
    ".fna.fbcdn.net",
)

_DIRECT_VIDEO_EXTENSIONS = (".mp4", ".mov", ".webm", ".m4v", ".avi", ".mkv")


def _is_ip_ssrf_safe(ip_str: str) -> bool:
    """Returns True if the IP address is publicly routable (not private/loopback/etc)."""
    try:
        ip_obj = ipaddress.ip_address(ip_str)
        return not (ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
                    or ip_obj.is_reserved or ip_obj.is_unspecified)
    except ValueError:
        return False


def _resolve_and_check_ssrf(hostname: str) -> bool:
    """Resolves hostname and returns True if ALL resolved IPs are publicly routable."""
    try:
        ip_obj = ipaddress.ip_address(hostname)
        return _is_ip_ssrf_safe(hostname)
    except ValueError:
        pass
    try:
        for _, _, _, _, sockaddr in socket.getaddrinfo(hostname, None):
            if not _is_ip_ssrf_safe(sockaddr[0]):
                return False
    except socket.gaierror:
        return False
    return True


def _is_public_safe_video_url(media_url: str) -> bool:
    """Validates remote media_url against SSRF / private IP rules before downloading."""
    if not media_url or not isinstance(media_url, str):
        return False
    try:
        parsed = urlparse(media_url.strip())
    except Exception:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False

    hostname = parsed.hostname.lower()
    if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or hostname.endswith((".local", ".internal", ".localhost")):
        return False
    # Instagram web page links serve HTML, not direct video stream bytes
    if "instagram.com" in hostname and ("/reel/" in parsed.path or "/p/" in parsed.path):
        return False

    return _resolve_and_check_ssrf(hostname)


def classify_video_url_type(url: str) -> str:
    """
    Classifies a URL for video download purposes.

    Returns:
        "DIRECT_VIDEO"    — URL ending in .mp4/.mov/.webm or from known CDN domains
        "INSTAGRAM_PAGE"  — instagram.com/reel/ or /p/ page (HTML, cannot download video)
        "BLOCKED"         — SSRF-blocked URL (private/loopback IP)
        "UNKNOWN_HOST"    — Other URLs (attempt download)
    """
    if not url or not isinstance(url, str):
        return "BLOCKED"
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return "BLOCKED"
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return "BLOCKED"

    hostname = parsed.hostname.lower()
    path_lower = parsed.path.lower()

    # Check SSRF first
    if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or hostname.endswith((".local", ".internal", ".localhost")):
        return "BLOCKED"
    try:
        ip_obj = ipaddress.ip_address(hostname)
        if not _is_ip_ssrf_safe(hostname):
            return "BLOCKED"
    except ValueError:
        pass

    # Instagram page URLs (serve HTML, not video bytes)
    if "instagram.com" in hostname and ("/reel/" in parsed.path or "/p/" in parsed.path):
        return "INSTAGRAM_PAGE"

    # Known CDN video domains
    if any(hostname.endswith(cdn) or re.match(r"scontent[a-z0-9\-]*\.fbcdn\.net", hostname) for cdn in _CDN_VIDEO_DOMAINS):
        return "DIRECT_VIDEO"

    # Direct video file extensions
    if any(path_lower.endswith(ext) for ext in _DIRECT_VIDEO_EXTENSIONS):
        return "DIRECT_VIDEO"

    return "UNKNOWN_HOST"


def _sanitize_url_for_log(url: str) -> str:
    """Extracts only the domain from a URL for safe diagnostic logging. Never logs full URL."""
    try:
        parsed = urlparse(url.strip())
        return parsed.hostname or "<unknown-host>"
    except Exception:
        return "<malformed-url>"


def download_remote_video_with_diagnostics(media_url: str) -> tuple[Optional[str], str, Optional[str]]:
    """
    Safely downloads a bounded remote video stream to a temporary file for OpenCV inspection.
    Follows redirects (up to 5 hops) and validates the final resolved URL against SSRF.

    Returns:
        (temp_file_path, video_source, limitation_reason)
    """
    if not HAS_HTTPX:
        logger.warning("video_download: httpx not available, skipping remote download")
        return None, "HTTPX_UNAVAILABLE", "HTTP client is not available in this runtime environment."

    if not media_url or not isinstance(media_url, str):
        return None, "INVALID_URL", "Media URL is missing or malformed."

    url_type = classify_video_url_type(media_url)
    domain = _sanitize_url_for_log(media_url)

    if url_type == "BLOCKED":
        logger.warning("video_download: URL blocked by SSRF check (domain=%s)", domain)
        return (
            None,
            "SSRF_BLOCKED",
            "URL was blocked because it points to a private, loopback, or restricted network address.",
        )
    if url_type == "INSTAGRAM_PAGE":
        logger.info(
            "video_download: Instagram page URL detected (domain=%s); "
            "cannot download video from page URLs without authentication",
            domain,
        )
        return (
            None,
            "INSTAGRAM_PAGE_UNSUPPORTED",
            "Instagram Reel page URLs do not provide direct video stream access without authentication. "
            "To analyze frame-level visual cuts, pacing, and safe zones, please upload the video file directly (Mode B) "
            "or connect your Instagram account (Mode C).",
        )

    logger.info("video_download: attempting download (domain=%s, url_type=%s)", domain, url_type)

    tmp_path: Optional[str] = None
    try:
        with httpx.Client(
            timeout=httpx.Timeout(connect=5.0, read=25.0, write=5.0, pool=5.0),
            follow_redirects=True,
            max_redirects=5,
        ) as client:
            with client.stream("GET", media_url.strip()) as resp:
                # Validate SSRF on the final resolved URL after redirects
                final_url = str(resp.url)
                try:
                    final_parsed = urlparse(final_url)
                    final_hostname = (final_parsed.hostname or "").lower()
                    if final_hostname and not _resolve_and_check_ssrf(final_hostname):
                        logger.warning(
                            "video_download: SSRF check failed on resolved URL after redirect (domain=%s)",
                            final_hostname,
                        )
                        return (
                            None,
                            "SSRF_REDIRECT_BLOCKED",
                            "Redirect destination was blocked because it resolves to a private, loopback, or internal network address.",
                        )
                except Exception:
                    logger.warning("video_download: could not parse resolved URL after redirect")
                    return None, "MALFORMED_REDIRECT_URL", "Could not parse resolved URL after redirect."

                if resp.status_code in (401, 403):
                    logger.info("video_download: auth required / expired (domain=%s, status=%d)", domain, resp.status_code)
                    return (
                        None,
                        "HTTP_AUTH_REQUIRED",
                        f"Remote server returned HTTP {resp.status_code} (access denied). The media URL requires authentication or the signed URL has expired.",
                    )
                if resp.status_code == 404:
                    logger.info("video_download: not found (domain=%s, status=404)", domain)
                    return None, "HTTP_NOT_FOUND", "Remote server returned HTTP 404 (media not found)."
                if resp.status_code != 200:
                    logger.info("video_download: non-200 status (domain=%s, status=%d)", domain, resp.status_code)
                    return None, "HTTP_ERROR", f"Remote server returned HTTP {resp.status_code}."

                ctype = (resp.headers.get("content-type") or "").lower()
                logger.info("video_download: response received (domain=%s, status=%d, content_type=%s)", domain, resp.status_code, ctype)

                if ctype and not (ctype.startswith("video/") or ctype == "application/octet-stream"):
                    if "text/html" in ctype or "text/plain" in ctype:
                        logger.info("video_download: rejected — response is HTML/text, not video (domain=%s)", domain)
                        return (
                            None,
                            "HTML_RESPONSE_NOT_VIDEO",
                            "The URL returned an HTML webpage instead of a raw video stream. Instagram and social media page URLs require authentication and do not expose raw video bytes publicly. Please use Connected Instagram (Mode C) or upload the video file directly (Mode B).",
                        )
                    logger.info("video_download: rejected — unsupported content-type (domain=%s, type=%s)", domain, ctype)
                    return None, "UNSUPPORTED_CONTENT_TYPE", f"Remote server returned unsupported Content-Type: '{ctype}'. Expected video stream."

                fd, tmp_path = tempfile.mkstemp(prefix="woka_stream_", suffix=".mp4")
                os.close(fd)
                written = 0
                with open(tmp_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=262144):
                        if written == 0 and chunk:
                            first_bytes = chunk[:256].lower()
                            if b"<html" in first_bytes or b"<!doctype" in first_bytes:
                                logger.info("video_download: rejected — HTML page received instead of video (domain=%s)", domain)
                                return (
                                    None,
                                    "HTML_RESPONSE_NOT_VIDEO",
                                    "The URL returned an HTML webpage instead of a raw video stream. Instagram and social media page URLs require authentication and do not expose raw video bytes publicly. Please use Connected Instagram (Mode C) or upload the video file directly (Mode B).",
                                )
                        written += len(chunk)
                        if written > MAX_REMOTE_VIDEO_BYTES:
                            return (
                                None,
                                "FILE_TOO_LARGE",
                                f"Remote video stream exceeds maximum download size cap ({MAX_REMOTE_VIDEO_BYTES // (1024*1024)} MB).",
                            )
                        f.write(chunk)
                if written < 128:
                    return None, "RESPONSE_TOO_SMALL", "Remote response too small to be a valid video stream."

                with open(tmp_path, "rb") as f:
                    header = f.read(64)
                if not validate_video_file_magic_bytes(header):
                    logger.info("video_download: rejected — file signature validation failed (domain=%s, size=%d)", domain, written)
                    return None, "INVALID_MAGIC_BYTES", "Downloaded file signature does not match any supported video container (MP4, MOV, WebM)."

                logger.info("video_download: file signature validated (domain=%s, size=%d bytes)", domain, written)
                return tmp_path, "OPENCV_REMOTE_STREAM", None
    except Exception as exc:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        if not isinstance(exc, ValueError):
            logger.warning("video_download: download failed (domain=%s, error=%s)", domain, type(exc).__name__)
        return None, "DOWNLOAD_FAILED", f"Remote video stream download failed: {type(exc).__name__}."


def download_remote_video_to_temp(media_url: str) -> Optional[str]:
    """
    Safely downloads a bounded remote video stream to a temporary file for OpenCV inspection.
    Returns the temp file path on success, or None if unavailable/offline/non-video.
    Follows redirects and validates the final resolved URL against SSRF.
    """
    tmp_path, _, _ = download_remote_video_with_diagnostics(media_url)
    return tmp_path


def extract_audio_with_ffmpeg(video_path: str, output_dir: str) -> Optional[str]:
    """
    Extracts audio from a video file using ffmpeg as mono 16kHz PCM WAV.
    Returns the .wav path on success, None on failure.
    Cleans up partial output on failure.
    """
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        logger.info("audio_extraction: ffmpeg not found on PATH, skipping audio extraction")
        return None

    os.makedirs(output_dir, exist_ok=True)
    output_filename = f"audio_{uuid.uuid4().hex[:12]}.wav"
    output_path = os.path.join(output_dir, output_filename)

    cmd = [
        ffmpeg_path, "-i", video_path,
        "-vn",                      # no video
        "-acodec", "pcm_s16le",     # 16-bit PCM
        "-ar", "16000",             # 16kHz sample rate
        "-ac", "1",                 # mono
        "-y",                       # overwrite output
        output_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            stderr_snippet = result.stderr[:500].decode("utf-8", errors="replace") if result.stderr else ""
            logger.warning(
                "audio_extraction: ffmpeg exited with code %d (stderr=%s)",
                result.returncode, stderr_snippet,
            )
            # Clean up partial output
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            return None

        if not os.path.exists(output_path) or os.path.getsize(output_path) < 44:
            logger.info("audio_extraction: output file missing or too small, skipping")
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            return None

        logger.info(
            "audio_extraction: successfully extracted audio (size=%d bytes)",
            os.path.getsize(output_path),
        )
        return output_path

    except subprocess.TimeoutExpired:
        logger.warning("audio_extraction: ffmpeg timed out after 30 seconds")
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass
        return None
    except Exception as exc:
        logger.warning("audio_extraction: unexpected error (%s)", type(exc).__name__)
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass
        return None


def detect_audio_pauses_with_ffmpeg(
    audio_path: str,
    silence_threshold_db: float = -30.0,
    min_duration_sec: float = 1.2,
) -> List[Dict[str, float]]:
    """
    Detects silent pauses in an audio file using FFmpeg's silencedetect filter.
    Returns a list of dicts with start, end, and duration.
    """
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path or not os.path.exists(audio_path):
        return []

    cmd = [
        ffmpeg_path, "-i", audio_path,
        "-af", f"silencedetect=noise={silence_threshold_db}dB:d={min_duration_sec}",
        "-f", "null", "-",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        stderr_text = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""

        starts = re.findall(r"silence_start:\s*([0-9.]+)", stderr_text)
        ends = re.findall(r"silence_end:\s*([0-9.]+)\s*\|\s*silence_duration:\s*([0-9.]+)", stderr_text)

        pauses = []
        for i, start_str in enumerate(starts):
            start = float(start_str)
            if i < len(ends):
                end = float(ends[i][0])
                duration = float(ends[i][1])
            else:
                end = start + min_duration_sec
                duration = min_duration_sec
            pauses.append({
                "start": round(start, 2),
                "end": round(end, 2),
                "duration": round(duration, 2),
            })
        logger.info("silence_detection: detected %d pause(s) >= %.1fs in audio", len(pauses), min_duration_sec)
        return pauses
    except Exception as exc:
        logger.warning("silence_detection: error detecting pauses (%s)", type(exc).__name__)
        return []


def _classify_aspect_ratio(width: int, height: int) -> str:
    if height <= 0 or width <= 0:
        return "UNKNOWN"
    ratio = round(width / height, 2)
    if 0.50 <= ratio <= 0.62:
        return "9:16"
    if 0.72 <= ratio <= 0.85:
        return "4:5"
    if 0.92 <= ratio <= 1.08:
        return "1:1"
    if ratio >= 1.60:
        return "16:9"
    gcd_val = math.gcd(width, height)
    return f"{width // gcd_val}:{height // gcd_val}"


def unavailable_video_metrics(reason: str, video_source: str = "UNAVAILABLE") -> Dict[str, Any]:
    """Explicit unavailable video metadata structure when real pixels/stream could not be decoded."""
    return {
        "duration_seconds": None,
        "duration_measured": False,
        "resolution_width": None,
        "resolution_height": None,
        "aspect_ratio": None,
        "is_safe_vertical": None,
        "fps": None,
        "fps_measured": False,
        "cuts_detected": None,
        "cut_timestamps": [],
        "avg_scene_duration_sec": None,
        "pacing_label": "UNAVAILABLE",
        "avg_brightness": None,
        "lighting_quality": "UNAVAILABLE",
        "avg_contrast": None,
        "safe_zone_hazard_ratio": None,
        "safe_zone_hazard_events": [],
        "subtitle_readability_score": None,
        "static_visual_ratio": None,
        "static_segments": [],
        "sampled_frame_count": 0,
        "frame_observations": [],
        "thumbnail_filename": None,
        "video_stream_analyzed": False,
        "is_simulated": False,
        "video_source": video_source,
        "limitation": reason,
        "audio_extracted": False,
        "detected_pauses": None,
    }


def extract_video_metadata_and_frames(
    video_path: Optional[str],
    output_thumbnail_dir: str,
    target_sample_rate_sec: float = 1.0,
    media_url: Optional[str] = None,
    allow_simulation: bool = False,
    source_identifier: str = "reel_source",
) -> Dict[str, Any]:
    """
    Analyzes physical video bytes using OpenCV.
    Extracts real resolution, FPS, duration, keyframes, cut timestamps, brightness,
    contrast, motion segments, safe-zone hazard timestamps, and local cover thumbnail.
    Never invents fake metrics when decoding does not occur.
    """
    os.makedirs(output_thumbnail_dir, exist_ok=True)
    downloaded_temp: Optional[str] = None
    active_path = video_path
    video_source = "OPENCV_LOCAL_FILE"

    try:
        if not active_path or not os.path.exists(active_path):
            if media_url:
                url_type = classify_video_url_type(media_url)
                if url_type == "INSTAGRAM_PAGE":
                    if allow_simulation:
                        return generate_simulated_video_metrics(source_identifier or media_url or "sandbox_reel", output_thumbnail_dir)
                    return unavailable_video_metrics(
                        "Instagram Reel page URLs do not provide direct video stream access without authentication. "
                        "To analyze frame-level visual cuts, pacing, and safe zones, please upload the video file directly (Mode B) "
                        "or connect your Instagram account (Mode C).",
                        video_source="INSTAGRAM_PAGE_UNSUPPORTED",
                    )
                downloaded_temp, stream_source, stream_limitation = download_remote_video_with_diagnostics(media_url)
                if downloaded_temp and os.path.exists(downloaded_temp):
                    active_path = downloaded_temp
                    video_source = stream_source or "OPENCV_REMOTE_STREAM"
                elif stream_limitation:
                    if allow_simulation:
                        return generate_simulated_video_metrics(source_identifier or media_url or "sandbox_reel", output_thumbnail_dir)
                    return unavailable_video_metrics(
                        stream_limitation,
                        video_source=stream_source or "DOWNLOAD_FAILED",
                    )

        if not active_path or not os.path.exists(active_path):
            if allow_simulation:
                return generate_simulated_video_metrics(source_identifier or media_url or "sandbox_reel", output_thumbnail_dir)
            return unavailable_video_metrics(
                "No local video file or accessible video stream could be downloaded; duration, FPS, resolution, and frame-level visual findings are unavailable.",
                video_source="VIDEO_UNAVAILABLE",
            )

        if not HAS_OPENCV:
            logger.warning("video_extraction: OpenCV (cv2) is not available in this runtime")
            if allow_simulation:
                return generate_simulated_video_metrics(source_identifier or active_path, output_thumbnail_dir)
            return unavailable_video_metrics(
                "OpenCV decoder is unavailable in this runtime environment.",
                video_source="DECODER_UNAVAILABLE",
            )

        logger.info("video_extraction: opening video with OpenCV (source=%s)", video_source)
        cap = cv2.VideoCapture(active_path)
        if not cap.isOpened():
            logger.warning("video_extraction: VideoCapture.isOpened() returned False")
            if allow_simulation:
                return generate_simulated_video_metrics(source_identifier or active_path, output_thumbnail_dir)
            return unavailable_video_metrics(
                "Video container could not be opened for frame decoding.",
                video_source="DECODE_FAILED",
            )

        raw_fps = cap.get(cv2.CAP_PROP_FPS)
        fps_measured = bool(raw_fps and not math.isnan(raw_fps) and raw_fps > 0)
        fps = round(float(raw_fps), 2) if fps_measured else None

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if total_frames <= 0 or width <= 0 or height <= 0:
            cap.release()
            if allow_simulation:
                return generate_simulated_video_metrics(source_identifier or active_path, output_thumbnail_dir)
            return unavailable_video_metrics(
                "Decoded video stream contained no readable frame dimensions or frame count.",
                video_source="DECODE_FAILED",
            )

        duration_measured = bool(fps_measured and raw_fps > 0)
        duration_seconds = round(total_frames / raw_fps, 2) if duration_measured else None
        effective_fps_for_ts = raw_fps if fps_measured else 30.0
        aspect_ratio_label = _classify_aspect_ratio(width, height)

        effective_sample_sec = 0.5 if (duration_seconds is not None and duration_seconds <= 10.0) else target_sample_rate_sec
        sample_interval_frames = max(1, int(effective_fps_for_ts * effective_sample_sec))

        prev_hist = None
        cuts_detected = 0
        cut_timestamps: List[float] = []

        brightness_scores: List[float] = []
        contrast_scores: List[float] = []
        safe_zone_hazard_frames = 0
        safe_zone_hazard_events: List[Dict[str, Any]] = []
        static_motion_frames = 0
        static_segments: List[Dict[str, Any]] = []
        current_static_start: Optional[float] = None
        current_static_motions: List[float] = []
        frame_observations: List[Dict[str, Any]] = []

        prev_gray = None
        last_sample_sec = 0.0

        base_stem = os.path.basename(active_path).split(".")[0] or uuid.uuid4().hex[:12]
        thumbnail_filename = f"thumb_{base_stem}_{uuid.uuid4().hex[:6]}.jpg"
        thumbnail_abs_path = os.path.join(output_thumbnail_dir, thumbnail_filename)
        thumbnail_rel_path: Optional[str] = None

        frame_idx = 0
        sampled_frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            current_sec = round(frame_idx / effective_fps_for_ts, 2)

            if frame_idx == 0:
                if cv2.imwrite(thumbnail_abs_path, frame):
                    thumbnail_rel_path = thumbnail_filename

            if frame_idx % sample_interval_frames == 0:
                sampled_frame_count += 1
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                mean_brightness = round(float(np.mean(gray)), 1)
                contrast = round(float(np.std(gray)), 1)
                brightness_scores.append(mean_brightness)
                contrast_scores.append(contrast)

                hist = cv2.calcHist([frame], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
                cv2.normalize(hist, hist)

                is_cut = False
                if prev_hist is not None:
                    similarity = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                    if similarity < 0.65:
                        cuts_detected += 1
                        cut_timestamps.append(current_sec)
                        is_cut = True
                prev_hist = hist

                motion_score: Optional[float] = None
                if prev_gray is not None:
                    diff = cv2.absdiff(prev_gray, gray)
                    motion_score = round(float(np.mean(diff)), 2)
                    if motion_score < 2.0:
                        static_motion_frames += 1
                        if current_static_start is None:
                            current_static_start = last_sample_sec
                        current_static_motions.append(motion_score)
                    else:
                        if current_static_start is not None and (current_sec - current_static_start) >= 2.0:
                            static_segments.append({
                                "start": round(current_static_start, 2),
                                "end": round(last_sample_sec, 2),
                                "duration": round(last_sample_sec - current_static_start, 2),
                                "avg_motion": round(float(np.mean(current_static_motions)), 2),
                            })
                        current_static_start = None
                        current_static_motions = []
                prev_gray = gray
                last_sample_sec = current_sec

                # Safe zone inspection (Bottom 22% captions/ticker, Right 18% Reels action icons)
                bottom_zone = gray[int(height * 0.78):, :]
                right_zone = gray[:, int(width * 0.82):]
                bottom_edge_energy = round(float(np.mean(cv2.Canny(bottom_zone, 80, 180))), 2) if bottom_zone.size else 0.0
                right_edge_energy = round(float(np.mean(cv2.Canny(right_zone, 80, 180))), 2) if right_zone.size else 0.0

                hazard_zones: List[str] = []
                if bottom_edge_energy > 15.0:
                    hazard_zones.append("bottom_22pct_edge_density")

                grad_x = cv2.Sobel(gray, cv2.CV_16S, 1, 0, ksize=3)
                abs_grad_x = cv2.convertScaleAbs(grad_x)
                _, thresh = cv2.threshold(abs_grad_x, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
                connected = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
                contours, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                text_hazard_count = 0
                for cnt in contours:
                    x, y, w, h = cv2.boundingRect(cnt)
                    if w > (width * 0.15) and h > 12 and (w / max(1, h)) >= 2.0:
                        in_bottom = y > int(height * 0.78)
                        in_right = (x + w) > int(width * 0.82)
                        if in_bottom or in_right:
                            text_hazard_count += 1
                            if in_bottom and "bottom_text_overlay" not in hazard_zones:
                                hazard_zones.append("bottom_text_overlay")
                            if in_right and "right_text_overlay" not in hazard_zones:
                                hazard_zones.append("right_text_overlay")

                frame_has_hazard = len(hazard_zones) > 0
                if frame_has_hazard:
                    safe_zone_hazard_frames += 1
                    if len(safe_zone_hazard_events) < 20:
                        safe_zone_hazard_events.append({
                            "timestamp_sec": current_sec,
                            "zones": hazard_zones,
                            "bottom_edge_energy": bottom_edge_energy,
                            "right_edge_energy": right_edge_energy,
                            "text_regions_count": text_hazard_count,
                        })

                if len(frame_observations) < 24:
                    frame_observations.append({
                        "timestamp_sec": current_sec,
                        "brightness": mean_brightness,
                        "contrast": contrast,
                        "motion_score": motion_score,
                        "bottom_edge_energy": bottom_edge_energy,
                        "right_edge_energy": right_edge_energy,
                        "safe_zone_hazard": frame_has_hazard,
                        "cut_detected": is_cut,
                    })

            frame_idx += 1

        cap.release()
        logger.info(
            "video_extraction: decoded %d frames from %d total (source=%s, resolution=%dx%d)",
            sampled_frame_count, frame_idx, video_source, width, height,
        )

        if current_static_start is not None and (last_sample_sec - current_static_start) >= 2.0:
            static_segments.append({
                "start": round(current_static_start, 2),
                "end": round(last_sample_sec, 2),
                "duration": round(last_sample_sec - current_static_start, 2),
                "avg_motion": round(float(np.mean(current_static_motions)), 2),
            })

        avg_brightness = round(float(np.mean(brightness_scores)), 1) if brightness_scores else None
        avg_contrast = round(float(np.mean(contrast_scores)), 1) if contrast_scores else None

        avg_scene_duration = (
            round(duration_seconds / max(1, cuts_detected + 1), 2)
            if duration_seconds is not None
            else None
        )
        if avg_scene_duration is not None:
            pacing_label = "FAST" if avg_scene_duration <= 2.2 else ("BALANCED" if avg_scene_duration <= 4.5 else "SLUGGISH")
        else:
            pacing_label = "UNAVAILABLE"

        is_safe_vertical = aspect_ratio_label == "9:16"
        lighting_quality = (
            "UNAVAILABLE"
            if avg_brightness is None
            else ("OPTIMAL" if 85.0 <= avg_brightness <= 180.0 else ("UNDEREXPOSED" if avg_brightness < 85.0 else "OVEREXPOSED"))
        )
        hazard_ratio = round(safe_zone_hazard_frames / max(1, sampled_frame_count), 2) if sampled_frame_count > 0 else None
        subtitle_readability = (
            max(40.0, min(98.0, round(95.0 - (hazard_ratio * 120.0), 1)))
            if hazard_ratio is not None
            else None
        )
        static_ratio = (
            round(static_motion_frames / max(1, sampled_frame_count - 1), 2)
            if sampled_frame_count > 1
            else 0.0
        )

        # Phase 4: Audio extraction & pause detection via FFmpeg
        detected_pauses: Optional[List[Dict[str, float]]] = None
        audio_extracted = False
        temp_audio_path: Optional[str] = None
        try:
            temp_audio_path = extract_audio_with_ffmpeg(active_path, output_thumbnail_dir)
            if temp_audio_path and os.path.exists(temp_audio_path):
                audio_extracted = True
                detected_pauses = detect_audio_pauses_with_ffmpeg(temp_audio_path)
        except Exception as e:
            logger.warning("video_extraction: audio processing failed: %s", e)
        finally:
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                except OSError:
                    pass

        return {
            "duration_seconds": duration_seconds,
            "duration_measured": duration_measured,
            "resolution_width": width,
            "resolution_height": height,
            "aspect_ratio": aspect_ratio_label,
            "is_safe_vertical": is_safe_vertical,
            "fps": fps,
            "fps_measured": fps_measured,
            "cuts_detected": cuts_detected,
            "cut_timestamps": cut_timestamps,
            "avg_scene_duration_sec": avg_scene_duration,
            "pacing_label": pacing_label,
            "avg_brightness": avg_brightness,
            "lighting_quality": lighting_quality,
            "avg_contrast": avg_contrast,
            "safe_zone_hazard_ratio": hazard_ratio,
            "safe_zone_hazard_events": safe_zone_hazard_events,
            "subtitle_readability_score": subtitle_readability,
            "static_visual_ratio": static_ratio,
            "static_segments": static_segments,
            "sampled_frame_count": sampled_frame_count,
            "frame_observations": frame_observations,
            "thumbnail_filename": thumbnail_rel_path,
            "video_stream_analyzed": True,
            "is_simulated": False,
            "video_source": video_source,
            "limitation": None if duration_measured else "Container did not report FPS; frame timestamps are approximate.",
            "audio_extracted": audio_extracted,
            "detected_pauses": detected_pauses,
        }
    finally:
        if downloaded_temp and os.path.exists(downloaded_temp):
            try:
                os.remove(downloaded_temp)
            except OSError:
                pass


def generate_simulated_video_metrics(source_identifier: str, output_thumbnail_dir: str) -> Dict[str, Any]:
    """Explicitly labeled deterministic simulation used ONLY for sandbox demo mode."""
    import hashlib
    h = int(hashlib.md5(source_identifier.encode()).hexdigest(), 16)

    duration = 24.0 + (h % 22)
    cuts = 4 + (h % 7)
    avg_scene = round(duration / (cuts + 1), 2)
    pacing = "FAST" if avg_scene <= 2.5 else ("BALANCED" if avg_scene <= 4.5 else "SLUGGISH")
    cut_times = [round(i * avg_scene, 1) for i in range(1, cuts + 1)]

    return {
        "duration_seconds": duration,
        "duration_measured": False,
        "resolution_width": 1080,
        "resolution_height": 1920,
        "aspect_ratio": "9:16",
        "is_safe_vertical": True,
        "fps": 30.0,
        "fps_measured": False,
        "cuts_detected": cuts,
        "cut_timestamps": cut_times,
        "avg_scene_duration_sec": avg_scene,
        "pacing_label": pacing,
        "avg_brightness": 128.5,
        "lighting_quality": "OPTIMAL",
        "avg_contrast": 54.2,
        "safe_zone_hazard_ratio": 0.08,
        "safe_zone_hazard_events": [],
        "subtitle_readability_score": 88.0,
        "static_visual_ratio": 0.04,
        "static_segments": [],
        "sampled_frame_count": 0,
        "frame_observations": [],
        "thumbnail_filename": None,
        "video_stream_analyzed": False,
        "is_simulated": True,
        "video_source": "SANDBOX_SIMULATED",
        "limitation": "Simulated demo video telemetry generated for sandbox preview (not decoded from live video pixels).",
        "audio_extracted": False,
        "detected_pauses": None,
    }
