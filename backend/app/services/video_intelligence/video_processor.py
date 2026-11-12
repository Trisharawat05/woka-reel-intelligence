import os
import math
import uuid
import tempfile
import ipaddress
import socket
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional
import numpy as np

from app.config import settings

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

    try:
        ip_obj = ipaddress.ip_address(hostname)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved or ip_obj.is_unspecified:
            return False
    except ValueError:
        try:
            for _, _, _, _, sockaddr in socket.getaddrinfo(hostname, None):
                resolved = ipaddress.ip_address(sockaddr[0])
                if resolved.is_private or resolved.is_loopback or resolved.is_link_local or resolved.is_reserved or resolved.is_unspecified:
                    return False
        except socket.gaierror:
            return False
    return True


def download_remote_video_to_temp(media_url: str) -> Optional[str]:
    """
    Safely downloads a bounded remote video stream to a temporary file for OpenCV inspection.
    Returns the temp file path on success, or None if unavailable/offline/non-video.
    """
    if (settings.ENVIRONMENT or "").lower() == "test":
        return None
    if not HAS_HTTPX or not _is_public_safe_video_url(media_url):
        return None

    tmp_path: Optional[str] = None
    try:
        with httpx.Client(timeout=httpx.Timeout(connect=3.0, read=6.0, write=3.0, pool=3.0), follow_redirects=False) as client:
            with client.stream("GET", media_url.strip()) as resp:
                if resp.status_code != 200:
                    return None
                ctype = (resp.headers.get("content-type") or "").lower()
                if ctype and not (ctype.startswith("video/") or ctype == "application/octet-stream"):
                    return None

                fd, tmp_path = tempfile.mkstemp(prefix="woka_stream_", suffix=".mp4")
                os.close(fd)
                written = 0
                with open(tmp_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=262144):
                        written += len(chunk)
                        if written > MAX_REMOTE_VIDEO_BYTES:
                            raise ValueError("Remote video stream exceeds analysis size cap.")
                        f.write(chunk)
                if written < 128:
                    raise ValueError("Remote response too small to be a valid video stream.")
                return tmp_path
    except Exception:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return None


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
                downloaded_temp = download_remote_video_to_temp(media_url)
                if downloaded_temp and os.path.exists(downloaded_temp):
                    active_path = downloaded_temp
                    video_source = "OPENCV_REMOTE_STREAM"

        if not active_path or not os.path.exists(active_path):
            if allow_simulation:
                return generate_simulated_video_metrics(source_identifier or media_url or "sandbox_reel", output_thumbnail_dir)
            return unavailable_video_metrics(
                "No local video file or accessible video stream could be downloaded; duration, FPS, resolution, and frame-level visual findings are unavailable."
            )

        if not HAS_OPENCV:
            if allow_simulation:
                return generate_simulated_video_metrics(source_identifier or active_path, output_thumbnail_dir)
            return unavailable_video_metrics(
                "OpenCV decoder is unavailable in this runtime environment.",
                video_source="DECODER_UNAVAILABLE",
            )

        cap = cv2.VideoCapture(active_path)
        if not cap.isOpened():
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
    }
