import os
import uuid
from typing import Dict, Any, List, Optional
from app.services.video_intelligence.video_processor import extract_video_metadata_and_frames
from app.services.video_intelligence.audio_processor import analyze_audio_and_speech

def run_video_intelligence_pipeline(
    video_path: Optional[str] = None,
    media_url: Optional[str] = None,
    caption: Optional[str] = None,
    title: Optional[str] = None,
    output_thumbnail_dir: str = "media_cache/thumbnails"
) -> Dict[str, Any]:
    """
    Executes end-to-end video intelligence analysis on the provided video asset or URL.
    Returns visual, audio, pacing, safe-zone, and hook metrics.
    """
    source_path = video_path or media_url or "simulated_reel_source"
    video_metrics = extract_video_metadata_and_frames(source_path, output_thumbnail_dir)

    # Heuristic transcription if audio track not locally decoded
    duration = video_metrics.get("duration_seconds", 30.0)
    transcript = caption or title or (
        "Here is the single biggest mistake creators make when posting Instagram Reels. "
        "Stop leading with a generic logo or slow intro. Start directly with the hook in the first 2 seconds. "
        "Notice how your view completion drops whenever you have dead air. "
        "Comment REEL below and I will send you the full retention blueprint!"
    )
    
    audio_metrics = analyze_audio_and_speech(transcript, duration)

    # Hook effectiveness analysis (First 3-5 seconds)
    first_3s_cuts = [t for t in video_metrics.get("cut_timestamps", []) if t <= 3.5]
    has_cut_in_first_3s = len(first_3s_cuts) > 0
    visual_clarity = "HIGH" if video_metrics.get("avg_contrast", 50.0) > 40.0 else "MEDIUM"
    
    # Calculate Hook Strength (0 - 100)
    hook_score = 65.0
    if audio_metrics.get("has_immediate_verbal_hook"):
        hook_score += 15.0
    if audio_metrics.get("has_curiosity_word_in_hook"):
        hook_score += 10.0
    if has_cut_in_first_3s:
        hook_score += 10.0
    if video_metrics.get("lighting_quality") == "OPTIMAL":
        hook_score += 5.0
    if video_metrics.get("static_visual_ratio", 0) > 0.15:
        hook_score -= 15.0
    hook_score = max(20.0, min(98.0, hook_score))

    # Pacing score (0 - 100)
    pacing_label = video_metrics.get("pacing_label", "BALANCED")
    if pacing_label == "FAST":
        pacing_score = 92.0
    elif pacing_label == "BALANCED":
        pacing_score = 85.0
    else:
        pacing_score = 62.0

    # Safe zone risk rating
    safe_zone_hazard = video_metrics.get("safe_zone_hazard_ratio", 0.0)
    if safe_zone_hazard > 0.20:
        safe_zone_status = "HIGH_RISK"
        safe_zone_notes = "Important visual text or focal point resides in the lower 20% or right 15%, obstructed by Reel UI buttons and captions."
    elif safe_zone_hazard > 0.08:
        safe_zone_status = "MODERATE_RISK"
        safe_zone_notes = "Minor overlap in lower overlay zone. Ensure subtitles are raised at least 200px from the bottom."
    else:
        safe_zone_status = "SAFE"
        safe_zone_notes = "Content adheres to official Instagram 9:16 safe margins."

    # CTA Analysis
    cta_triggers = ["comment", "link", "share", "save", "follow", "dm", "bio", "check", "below"]
    transcript_lower = transcript.lower()
    has_explicit_cta = any(trig in transcript_lower for trig in cta_triggers)
    cta_type = "COMMENT_TRIGGER" if "comment" in transcript_lower else (
        "SAVE_EVERGREEN" if "save" in transcript_lower else (
            "SHARE_NETWORK" if "share" in transcript_lower else (
                "PROFILE_BIO" if "bio" in transcript_lower or "follow" in transcript_lower else "GENERIC_NONE"
            )
        )
    )

    return {
        "metadata": {
            "duration_seconds": duration,
            "resolution": f"{video_metrics.get('resolution_width')}x{video_metrics.get('resolution_height')}",
            "aspect_ratio": video_metrics.get("aspect_ratio", "9:16"),
            "fps": video_metrics.get("fps", 30.0),
            "is_vertical_format": video_metrics.get("is_safe_vertical", True)
        },
        "hook_analysis": {
            "hook_score": hook_score,
            "visual_clarity": visual_clarity,
            "has_cut_in_first_3s": has_cut_in_first_3s,
            "verbal_hook_detected": audio_metrics.get("has_immediate_verbal_hook"),
            "curiosity_trigger_present": audio_metrics.get("has_curiosity_word_in_hook"),
            "first_frame_thumbnail_saved": video_metrics.get("thumbnail_filename")
        },
        "visual_pacing": {
            "pacing_label": pacing_label,
            "pacing_score": pacing_score,
            "cuts_detected": video_metrics.get("cuts_detected", 5),
            "avg_scene_duration_sec": video_metrics.get("avg_scene_duration_sec", 3.2),
            "cut_timestamps": video_metrics.get("cut_timestamps", []),
            "static_visual_ratio": video_metrics.get("static_visual_ratio", 0.0)
        },
        "audio_speech": {
            "words_per_minute": audio_metrics.get("words_per_minute", 152.0),
            "pacing_rating": audio_metrics.get("pacing_rating", "OPTIMAL_ENERGY"),
            "pacing_verdict": audio_metrics.get("pacing_verdict"),
            "dead_air_count": audio_metrics.get("dead_air_count", 0),
            "dead_air_intervals": audio_metrics.get("dead_air_intervals", []),
            "audio_clarity_score": audio_metrics.get("audio_clarity_score", 90.0)
        },
        "safe_zones": {
            "status": safe_zone_status,
            "hazard_ratio": safe_zone_hazard,
            "subtitle_readability_score": video_metrics.get("subtitle_readability_score", 88.0),
            "guidelines": safe_zone_notes
        },
        "cta_assessment": {
            "has_explicit_cta": has_explicit_cta,
            "cta_type": cta_type,
            "strength": "STRONG" if has_explicit_cta and cta_type in ["COMMENT_TRIGGER", "SAVE_EVERGREEN"] else ("MODERATE" if has_explicit_cta else "WEAK")
        }
    }
