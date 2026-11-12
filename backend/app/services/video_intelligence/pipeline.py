import re
from typing import Dict, Any, List, Optional
from app.services.video_intelligence.video_processor import extract_video_metadata_and_frames
from app.services.video_intelligence.audio_processor import analyze_audio_and_speech

_STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "you", "your", "are", "was", "were",
    "have", "has", "had", "not", "but", "what", "how", "why", "when", "where", "who",
    "from", "into", "about", "just", "here", "there", "they", "them", "will", "would",
    "could", "should", "can", "all", "one", "two", "more", "most", "very", "too",
    "out", "below", "above", "reel", "reels", "instagram", "video", "post", "sandbox", "public", "uploaded",
}


def _extract_caption_analysis(
    caption: Optional[str],
    title: Optional[str],
    original_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """Extracts verified topic keywords, hashtags, opening text, and CTA triggers from actual Reel text."""
    clean_caption = (caption or "").strip()
    clean_title = (title or "").strip()
    is_synthetic_title = (
        clean_title.startswith("Public Reel")
        or clean_title.startswith("Uploaded Reel")
        or clean_title.startswith("Uploaded Video")
        or clean_title.startswith("Connected Reel")
        or clean_title.startswith("Reel Analysis")
        or clean_title in ("Public Video Analysis", "Instagram Reel")
    )
    effective_title = "" if is_synthetic_title else clean_title
    combined = clean_caption or effective_title

    hashtags = re.findall(r"#[A-Za-z0-9_]+", combined)
    without_urls = re.sub(r"https?://\S+", "", combined)
    without_tags = re.sub(r"#[A-Za-z0-9_]+", "", without_urls).strip()

    first_line = ""
    if without_tags:
        first_line = re.split(r"[\n.!?]+", without_tags)[0].strip()

    # Keyword tokens for Reel-specific topic grounding
    tokens = re.findall(r"[A-Za-z0-9']{3,}", without_tags.lower())
    keywords: List[str] = []
    for tok in tokens:
        if tok not in _STOPWORDS and not tok.isdigit() and tok not in keywords:
            keywords.append(tok)
        if len(keywords) >= 8:
            break

    # Extract topic hints from descriptive upload filename when caption/title don't supply keywords
    filename_hint = ""
    if original_filename:
        stem = re.sub(r"^[0-9a-f\-]{36}_", "", original_filename).rsplit(".", 1)[0]
        stem_clean = re.sub(r"[_\-]+", " ", stem).strip()
        if stem_clean and stem_clean.lower() not in ("upload", "uploaded reel", "video", "reel"):
            filename_hint = stem_clean
            if not keywords:
                for tok in re.findall(r"[A-Za-z0-9']{3,}", stem_clean.lower()):
                    if tok not in _STOPWORDS and not tok.isdigit() and tok not in keywords:
                        keywords.append(tok)
                    if len(keywords) >= 5:
                        break

    curiosity_triggers = ["why", "how", "stop", "secret", "never", "mistake", "if you", "nobody", "trick", "guide", "?"]
    opening_lower = (first_line or combined).lower()
    matched_hook_triggers = [
        trig for trig in curiosity_triggers
        if (trig == "?" and "?" in (first_line or combined)) or (trig != "?" and re.search(r"\b" + re.escape(trig) + r"\b", opening_lower))
    ]

    cta_triggers = ["comment", "link", "share", "save", "follow", "dm", "bio", "check", "below", "reply"]
    combined_lower = combined.lower()
    matched_cta_keywords = [
        trig for trig in cta_triggers if re.search(r"\b" + re.escape(trig) + r"\b", combined_lower)
    ]

    if "comment" in matched_cta_keywords or "dm" in matched_cta_keywords or "reply" in matched_cta_keywords:
        cta_type = "COMMENT_OR_DM_TRIGGER"
    elif "save" in matched_cta_keywords:
        cta_type = "SAVE_PROMPT"
    elif "share" in matched_cta_keywords:
        cta_type = "SHARE_PROMPT"
    elif "bio" in matched_cta_keywords or "follow" in matched_cta_keywords or "link" in matched_cta_keywords:
        cta_type = "PROFILE_OR_LINK_CTA"
    elif combined:
        cta_type = "NONE_DETECTED_IN_CAPTION"
    else:
        cta_type = "UNAVAILABLE_NO_TEXT"

    has_explicit_cta = len(matched_cta_keywords) > 0
    cta_strength = (
        "STRONG"
        if has_explicit_cta and cta_type in ("COMMENT_OR_DM_TRIGGER", "SAVE_PROMPT")
        else ("MODERATE" if has_explicit_cta else ("WEAK" if combined else "UNAVAILABLE"))
    )

    return {
        "caption_present": bool(clean_caption),
        "title_present": bool(clean_title),
        "has_text_context": bool(combined),
        "opening_line": first_line,
        "full_text": combined,
        "filename_hint": filename_hint,
        "topic_keywords": keywords,
        "hashtags": hashtags[:8],
        "matched_hook_triggers": matched_hook_triggers,
        "has_caption_hook_trigger": len(matched_hook_triggers) > 0,
        "has_explicit_cta": has_explicit_cta,
        "matched_cta_keywords": matched_cta_keywords,
        "cta_type": cta_type,
        "cta_strength": cta_strength,
    }


def run_video_intelligence_pipeline(
    video_path: Optional[str] = None,
    media_url: Optional[str] = None,
    caption: Optional[str] = None,
    title: Optional[str] = None,
    output_thumbnail_dir: str = "media_cache/thumbnails",
    allow_simulation: bool = False,
    source_identifier: Optional[str] = None,
    transcript_override: Optional[str] = None,
    detected_pauses: Optional[List[Dict[str, float]]] = None,
    original_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes grounded video intelligence analysis on a Reel file, stream, or metadata context.
    Separates decoded pixel/frame facts from unmeasured audio or unavailable remote video.
    """
    source_id = source_identifier or video_path or media_url or "reel_source"
    video_metrics = extract_video_metadata_and_frames(
        video_path=video_path,
        output_thumbnail_dir=output_thumbnail_dir,
        media_url=media_url,
        allow_simulation=allow_simulation,
        source_identifier=source_id,
    )

    stream_analyzed = bool(video_metrics.get("video_stream_analyzed"))
    is_simulated = bool(video_metrics.get("is_simulated"))
    duration = video_metrics.get("duration_seconds")

    # Never synthesize spoken WPM or dead-air pauses from a fake boilerplate transcript
    if transcript_override and transcript_override.strip():
        audio_duration = float(duration) if duration else 30.0
        audio_metrics = analyze_audio_and_speech(
            transcript_override,
            audio_duration,
            detected_pauses=detected_pauses,
        )
        audio_metrics["audio_analysis_available"] = True
        audio_metrics["audio_source"] = "AUDIO_TRANSCRIPT"
    elif detected_pauses is not None:
        long_pauses = [p for p in detected_pauses if (p.get("end", 0) - p.get("start", 0)) >= 1.2]
        audio_metrics = {
            "word_count": None,
            "words_per_minute": None,
            "pacing_rating": "UNAVAILABLE",
            "pacing_verdict": "Audio pauses supplied without speech transcript; WPM is unavailable.",
            "dead_air_count": len(long_pauses),
            "dead_air_intervals": long_pauses,
            "has_immediate_verbal_hook": None,
            "has_curiosity_word_in_hook": None,
            "audio_clarity_score": None,
            "subtitles_synced": None,
            "audio_analysis_available": True,
            "audio_source": "AUDIO_PAUSE_TELEMETRY",
        }
    else:
        audio_metrics = {
            "word_count": None,
            "words_per_minute": None,
            "pacing_rating": "UNAVAILABLE",
            "pacing_verdict": "Spoken audio transcription is not available in this environment; WPM and audio dead-air pauses were not measured.",
            "dead_air_count": None,
            "dead_air_intervals": [],
            "has_immediate_verbal_hook": None,
            "has_curiosity_word_in_hook": None,
            "audio_clarity_score": None,
            "subtitles_synced": None,
            "audio_analysis_available": False,
            "audio_source": "UNAVAILABLE",
        }

    text_context = _extract_caption_analysis(caption, title, original_filename=original_filename)

    cut_timestamps = video_metrics.get("cut_timestamps") or []
    first_3s_cuts = [t for t in cut_timestamps if t <= 3.5] if (stream_analyzed or is_simulated) else []
    has_cut_in_first_3s: Optional[bool] = (len(first_3s_cuts) > 0) if (stream_analyzed or is_simulated) else None

    avg_contrast = video_metrics.get("avg_contrast")
    if avg_contrast is None:
        visual_clarity = "UNAVAILABLE"
    elif avg_contrast > 40.0:
        visual_clarity = "HIGH"
    elif avg_contrast >= 20.0:
        visual_clarity = "MEDIUM"
    else:
        visual_clarity = "LOW"

    # Grounded Hook Score (None if neither pixels nor text context available)
    if stream_analyzed or is_simulated:
        hook_score: Optional[float] = 55.0
        if has_cut_in_first_3s:
            hook_score += 18.0
        if video_metrics.get("lighting_quality") == "OPTIMAL":
            hook_score += 8.0
        if avg_contrast is not None and avg_contrast > 35.0:
            hook_score += 7.0
        if text_context["has_caption_hook_trigger"]:
            hook_score += 10.0
        if audio_metrics.get("has_curiosity_word_in_hook"):
            hook_score += 7.0
        static_ratio = video_metrics.get("static_visual_ratio") or 0.0
        if static_ratio > 0.25:
            hook_score -= 15.0
        hook_score = round(max(20.0, min(98.0, hook_score)), 1)
    elif text_context["has_text_context"]:
        # Partial text-only hook signal (no decoded pixels)
        hook_score = 72.0 if text_context["has_caption_hook_trigger"] else 54.0
    else:
        hook_score = None

    # Pacing Score
    pacing_label = video_metrics.get("pacing_label", "UNAVAILABLE")
    if pacing_label == "FAST":
        pacing_score: Optional[float] = 92.0
    elif pacing_label == "BALANCED":
        pacing_score = 82.0
    elif pacing_label == "SLUGGISH":
        pacing_score = 56.0
    else:
        pacing_score = None

    # Safe zone risk rating
    safe_zone_hazard = video_metrics.get("safe_zone_hazard_ratio")
    hazard_events = video_metrics.get("safe_zone_hazard_events") or []
    if safe_zone_hazard is None:
        safe_zone_status = "UNAVAILABLE"
        safe_zone_notes = "Safe-zone pixel checks unavailable because video frames were not decoded."
    elif safe_zone_hazard > 0.20:
        safe_zone_status = "HIGH_RISK"
        sample_ts = ", ".join(f"{e['timestamp_sec']}s" for e in hazard_events[:4])
        safe_zone_notes = (
            f"Detected high edge/text density in Instagram UI bottom 22% / right 18% zones "
            f"across {round(safe_zone_hazard * 100)}% of sampled frames"
            + (f" (observed at {sample_ts})." if sample_ts else ".")
        )
    elif safe_zone_hazard > 0.08:
        safe_zone_status = "MODERATE_RISK"
        sample_ts = ", ".join(f"{e['timestamp_sec']}s" for e in hazard_events[:4])
        safe_zone_notes = (
            f"Detected occasional edge/text density near lower/right UI margins across {round(safe_zone_hazard * 100)}% of sampled frames"
            + (f" (observed at {sample_ts})." if sample_ts else ".")
        )
    else:
        safe_zone_status = "SAFE"
        safe_zone_notes = (
            f"Bottom 22% and right 18% UI overlay regions remained clear across {video_metrics.get('sampled_frame_count', 0)} sampled frame(s)."
            if stream_analyzed
            else "Simulated sample margins adhere to Instagram 9:16 safe margins."
        )

    width = video_metrics.get("resolution_width")
    height = video_metrics.get("resolution_height")
    resolution_str = f"{width}x{height}" if (width and height) else None

    return {
        "metadata": {
            "duration_seconds": duration,
            "duration_measured": bool(video_metrics.get("duration_measured")),
            "resolution": resolution_str,
            "resolution_width": width,
            "resolution_height": height,
            "aspect_ratio": video_metrics.get("aspect_ratio"),
            "fps": video_metrics.get("fps"),
            "fps_measured": bool(video_metrics.get("fps_measured")),
            "is_vertical_format": video_metrics.get("is_safe_vertical"),
            "video_stream_analyzed": stream_analyzed,
            "is_simulated": is_simulated,
            "video_source": video_metrics.get("video_source", "UNAVAILABLE"),
            "sampled_frame_count": video_metrics.get("sampled_frame_count", 0),
            "limitation": video_metrics.get("limitation"),
        },
        "frame_telemetry": {
            "frame_observations": video_metrics.get("frame_observations", []),
            "avg_brightness": video_metrics.get("avg_brightness"),
            "lighting_quality": video_metrics.get("lighting_quality", "UNAVAILABLE"),
            "avg_contrast": avg_contrast,
            "static_segments": video_metrics.get("static_segments", []),
            "safe_zone_hazard_events": hazard_events,
        },
        "hook_analysis": {
            "hook_score": hook_score,
            "visual_clarity": visual_clarity,
            "has_cut_in_first_3s": has_cut_in_first_3s,
            "first_3s_cut_timestamps": first_3s_cuts,
            "verbal_hook_detected": audio_metrics.get("has_immediate_verbal_hook"),
            "curiosity_trigger_present": audio_metrics.get("has_curiosity_word_in_hook") if audio_metrics.get("audio_analysis_available") else text_context["has_caption_hook_trigger"],
            "caption_hook_triggers": text_context["matched_hook_triggers"],
            "first_frame_thumbnail_saved": video_metrics.get("thumbnail_filename"),
        },
        "visual_pacing": {
            "pacing_label": pacing_label,
            "pacing_score": pacing_score,
            "cuts_detected": video_metrics.get("cuts_detected"),
            "avg_scene_duration_sec": video_metrics.get("avg_scene_duration_sec"),
            "cut_timestamps": cut_timestamps,
            "static_visual_ratio": video_metrics.get("static_visual_ratio"),
            "static_segments": video_metrics.get("static_segments", []),
        },
        "audio_speech": audio_metrics,
        "safe_zones": {
            "status": safe_zone_status,
            "hazard_ratio": safe_zone_hazard,
            "hazard_events": hazard_events,
            "subtitle_readability_score": video_metrics.get("subtitle_readability_score"),
            "guidelines": safe_zone_notes,
        },
        "text_context": text_context,
        "cta_assessment": {
            "has_explicit_cta": text_context["has_explicit_cta"],
            "cta_type": text_context["cta_type"],
            "matched_keywords": text_context["matched_cta_keywords"],
            "strength": text_context["cta_strength"],
            "evaluated_from": "CAPTION_AND_TITLE" if text_context["has_text_context"] else "UNAVAILABLE",
        },
    }
