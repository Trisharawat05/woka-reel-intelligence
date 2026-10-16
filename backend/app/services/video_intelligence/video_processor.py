import os
import math
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def extract_video_metadata_and_frames(
    video_path: str,
    output_thumbnail_dir: str,
    target_sample_rate_sec: float = 1.0
) -> Dict[str, Any]:
    """
    Analyzes physical video file using OpenCV.
    Extracts keyframe samples, detects scene transitions, calculates lighting,
    computes contrast, checks safe zones, and generates cover thumbnail.
    """
    os.makedirs(output_thumbnail_dir, exist_ok=True)
    thumbnail_rel_path = None

    if not os.path.exists(video_path) or not HAS_OPENCV:
        # Fallback heuristic for simulated/mock/direct URL without local file
        return generate_simulated_video_metrics(video_path, output_thumbnail_dir)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return generate_simulated_video_metrics(video_path, output_thumbnail_dir)

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or math.isnan(fps) or fps <= 0:
        fps = 30.0

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    if total_frames <= 0 or width <= 0 or height <= 0:
        cap.release()
        return generate_simulated_video_metrics(video_path, output_thumbnail_dir)

    duration_seconds = round(total_frames / fps, 2)
    aspect_ratio_num = round(width / height, 2) if height > 0 else 0.56
    aspect_ratio_label = "9:16" if 0.50 <= aspect_ratio_num <= 0.62 else ("16:9" if aspect_ratio_num >= 1.6 else "4:5")

    # Sample frames across timeline
    sample_interval_frames = max(1, int(fps * target_sample_rate_sec))
    prev_hist = None
    cuts_detected = 0
    cut_timestamps: List[float] = []
    
    brightness_scores: List[float] = []
    contrast_scores: List[float] = []
    safe_zone_hazard_count = 0
    static_motion_frames = 0
    prev_gray = None

    thumbnail_filename = f"thumb_{os.path.basename(video_path).split('.')[0]}.jpg"
    thumbnail_abs_path = os.path.join(output_thumbnail_dir, thumbnail_filename)

    frame_idx = 0
    sampled_frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_sec = round(frame_idx / fps, 2)

        # Save First frame as thumbnail
        if frame_idx == 0:
            cv2.imwrite(thumbnail_abs_path, frame)
            thumbnail_rel_path = thumbnail_filename

        if frame_idx % sample_interval_frames == 0:
            sampled_frame_count += 1
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Brightness & contrast
            mean_brightness = float(np.mean(gray))
            contrast = float(np.std(gray))
            brightness_scores.append(mean_brightness)
            contrast_scores.append(contrast)

            # Color histogram for scene cut detection
            hist = cv2.calcHist([frame], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            cv2.normalize(hist, hist)
            
            if prev_hist is not None:
                similarity = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                if similarity < 0.65:  # Significant scene difference indicates a cut
                    cuts_detected += 1
                    cut_timestamps.append(current_sec)

            prev_hist = hist

            # Motion detection (detecting dead air / frozen visual)
            if prev_gray is not None:
                diff = cv2.absdiff(prev_gray, gray)
                motion_score = float(np.mean(diff))
                if motion_score < 2.0:  # virtually no visual change
                    static_motion_frames += 1

            prev_gray = gray

            # Safe Zone Hazard Check: Instagram Reel overlays
            # Bottom 20% contains captions and sound title; Right 18% has action buttons
            bottom_zone = gray[int(height * 0.78):, :]
            right_zone = gray[:, int(width * 0.82):]
            
            # High edge energy in obstructed zones indicates text/graphics risked being covered
            edges_bottom = cv2.Canny(bottom_zone, 80, 180)
            if float(np.mean(edges_bottom)) > 15.0:
                safe_zone_hazard_count += 1

            # OCR / Text line candidate detection using morphological horizontal gradient
            # Connects horizontally adjacent character glyphs in middle reading zone
            grad_x = cv2.Sobel(gray, cv2.CV_16S, 1, 0, ksize=3)
            abs_grad_x = cv2.convertScaleAbs(grad_x)
            _, thresh = cv2.threshold(abs_grad_x, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
            connected = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                if w > (width * 0.15) and h > 12 and (w / max(1, h)) >= 2.0:
                    # Bounding box matches a line of text/subtitle
                    if y > int(height * 0.78) or (x + w) > int(width * 0.82):
                        safe_zone_hazard_count += 1

        frame_idx += 1

    cap.release()

    avg_brightness = round(float(np.mean(brightness_scores)), 1) if brightness_scores else 120.0
    avg_contrast = round(float(np.mean(contrast_scores)), 1) if contrast_scores else 48.0
    
    avg_scene_duration = round(duration_seconds / max(1, cuts_detected + 1), 2)
    pacing_label = "FAST" if avg_scene_duration <= 2.2 else ("BALANCED" if avg_scene_duration <= 4.5 else "SLUGGISH")

    is_safe_vertical = (aspect_ratio_label == "9:16")
    lighting_quality = "OPTIMAL" if 85.0 <= avg_brightness <= 180.0 else ("UNDEREXPOSED" if avg_brightness < 85.0 else "OVEREXPOSED")
    hazard_ratio = round(safe_zone_hazard_count / max(1, sampled_frame_count), 2)
    subtitle_readability = max(40.0, min(98.0, round(95.0 - (hazard_ratio * 120.0), 1)))

    return {
        "duration_seconds": duration_seconds,
        "resolution_width": width,
        "resolution_height": height,
        "aspect_ratio": aspect_ratio_label,
        "is_safe_vertical": is_safe_vertical,
        "fps": fps,
        "cuts_detected": cuts_detected,
        "cut_timestamps": cut_timestamps,
        "avg_scene_duration_sec": avg_scene_duration,
        "pacing_label": pacing_label,
        "avg_brightness": avg_brightness,
        "lighting_quality": lighting_quality,
        "avg_contrast": avg_contrast,
        "safe_zone_hazard_ratio": hazard_ratio,
        "subtitle_readability_score": subtitle_readability,
        "static_visual_ratio": round(static_motion_frames / max(1, sampled_frame_count), 2),
        "thumbnail_filename": thumbnail_rel_path,
        "is_simulated": False
    }


def generate_simulated_video_metrics(source_identifier: str, output_thumbnail_dir: str) -> Dict[str, Any]:
    """Deterministic simulation when direct video decoding is remote or media is mock."""
    import hashlib
    h = int(hashlib.md5(source_identifier.encode()).hexdigest(), 16)
    
    duration = 24.0 + (h % 22)  # 24 to 45 seconds
    cuts = 4 + (h % 7)           # 4 to 10 cuts
    avg_scene = round(duration / (cuts + 1), 2)
    pacing = "FAST" if avg_scene <= 2.5 else ("BALANCED" if avg_scene <= 4.5 else "SLUGGISH")
    
    cut_times = [round(i * avg_scene, 1) for i in range(1, cuts + 1)]

    return {
        "duration_seconds": duration,
        "resolution_width": 1080,
        "resolution_height": 1920,
        "aspect_ratio": "9:16",
        "is_safe_vertical": True,
        "fps": 30.0,
        "cuts_detected": cuts,
        "cut_timestamps": cut_times,
        "avg_scene_duration_sec": avg_scene,
        "pacing_label": pacing,
        "avg_brightness": 128.5,
        "lighting_quality": "OPTIMAL",
        "avg_contrast": 54.2,
        "safe_zone_hazard_ratio": 0.08,
        "subtitle_readability_score": 88.0,
        "static_visual_ratio": 0.04,
        "thumbnail_filename": None,
        "is_simulated": True
    }
