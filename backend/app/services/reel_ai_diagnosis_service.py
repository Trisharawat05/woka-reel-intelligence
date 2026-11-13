import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


def compute_rating_label(score: float, data_available: bool = True) -> str:
    if not data_available:
        return "UNAVAILABLE"
    if score >= 88.0:
        return "EXCEPTIONAL"
    if score >= 75.0:
        return "STRONG"
    if score >= 60.0:
        return "MODERATE"
    return "UNDERPERFORMING"


def compute_component_status(score: float, data_available: bool = True) -> str:
    if not data_available:
        return "UNAVAILABLE"
    if score >= 85.0:
        return "EXCELLENT"
    if score >= 70.0:
        return "GOOD"
    if score >= 55.0:
        return "NEEDS_IMPROVEMENT"
    return "POOR"


def _fmt_sec(sec: float) -> str:
    s = max(0, int(round(sec)))
    return f"{s // 60:02d}:{s % 60:02d}"


def _derive_topic_context(
    title: Optional[str],
    caption: Optional[str],
    video_intel: Dict[str, Any],
    video_filename: Optional[str] = None,
) -> Dict[str, Any]:
    text_ctx = video_intel.get("text_context") or {}
    clean_title = (title or "").strip()
    clean_caption = (caption or "").strip()
    has_real_text = bool(text_ctx.get("has_text_context")) if "has_text_context" in text_ctx else bool(clean_caption or clean_title)
    opening_line = (text_ctx.get("opening_line") or clean_caption or "").strip()
    keywords: List[str] = list(text_ctx.get("topic_keywords") or [])
    hashtags: List[str] = list(text_ctx.get("hashtags") or [])
    filename_hint = (text_ctx.get("filename_hint") or "").strip()

    is_synthetic_title = (
        clean_title.startswith("Public Reel")
        or clean_title.startswith("Uploaded Reel")
        or clean_title.startswith("Uploaded Video")
        or clean_title.startswith("Connected Reel")
        or clean_title.startswith("Reel Analysis")
        or clean_title in ("Public Video Analysis", "Instagram Reel")
    )

    if keywords:
        topic_phrase = " ".join(keywords[:3])
    elif filename_hint:
        topic_phrase = filename_hint[:45]
    elif clean_title and not is_synthetic_title:
        topic_phrase = clean_title[:50]
    else:
        topic_phrase = ""

    if not hashtags and keywords:
        hashtags = [f"#{k.replace('-', '').replace(' ', '')}" for k in keywords[:4]]

    return {
        "has_text": has_real_text,
        "title": clean_title,
        "caption": clean_caption,
        "opening_line": opening_line,
        "topic_phrase": topic_phrase,
        "keywords": keywords,
        "hashtags": hashtags,
        "hashtag_line": " ".join(hashtags[:5]) if hashtags else "",
        "filename_hint": filename_hint or (video_filename or ""),
    }


def _reweighted_average(entries: List[tuple[Optional[float], float]]) -> Optional[float]:
    valid = [(val, weight) for val, weight in entries if val is not None and weight > 0]
    if not valid:
        return None
    total_w = sum(w for _, w in valid)
    if total_w <= 0:
        return None
    return round(sum(val * w for val, w in valid) / total_w, 1)


def generate_ai_diagnosis_report(
    video_intel: Dict[str, Any],
    performance_metrics: Dict[str, Any],
    caption: Optional[str] = None,
    title: Optional[str] = None,
    analysis_mode: str = "PUBLIC_URL",
    video_filename: Optional[str] = None,
    timestamped_retention_available: bool = False,
) -> Dict[str, Any]:
    """
    Synthesizes decoded frame telemetry, caption/copy context, and verified metrics into
    grounded scores, timestamped findings, action plan steps, and Reel-specific alternatives.
    Never invents fake confidence, retention, or unrelated template content.
    """
    is_connected = analysis_mode == "CONNECTED_ACCOUNT"
    meta = video_intel.get("metadata") or {}
    frame_tel = video_intel.get("frame_telemetry") or {}
    hook_intel = video_intel.get("hook_analysis") or {}
    pacing_intel = video_intel.get("visual_pacing") or {}
    audio_intel = video_intel.get("audio_speech") or {}
    safe_intel = video_intel.get("safe_zones") or {}
    cta_intel = video_intel.get("cta_assessment") or {}

    stream_analyzed = bool(meta.get("video_stream_analyzed"))
    is_simulated_video = bool(meta.get("is_simulated"))
    is_simulated_metrics = any(bool(m.get("is_simulated")) for m in performance_metrics.values() if isinstance(m, dict))
    is_simulated = is_simulated_video or is_simulated_metrics

    duration_raw = meta.get("duration_seconds")
    duration_measured = bool(meta.get("duration_measured") and duration_raw is not None)
    duration = float(duration_raw) if duration_raw is not None else None
    fps_val = meta.get("fps")
    resolution_str = meta.get("resolution")
    aspect_ratio = meta.get("aspect_ratio")
    sampled_frames = int(meta.get("sampled_frame_count") or 0)

    topic = _derive_topic_context(title, caption, video_intel, video_filename=video_filename)
    has_visual_telemetry = stream_analyzed or is_simulated_video
    audio_available = bool(audio_intel.get("audio_analysis_available"))

    # --------------------------------------------------------------------------
    # 1. Creative Quality & Sub-Dimensions
    # --------------------------------------------------------------------------
    hook_subscore: Optional[float] = hook_intel.get("hook_score")
    if hook_subscore is not None:
        hook_subscore = float(hook_subscore)

    pacing_subscore: Optional[float] = pacing_intel.get("pacing_score")
    if pacing_subscore is not None:
        pacing_subscore = float(pacing_subscore)

    audio_subscore: Optional[float] = audio_intel.get("audio_clarity_score")
    if audio_subscore is not None:
        audio_subscore = float(audio_subscore)

    safe_zones_status = safe_intel.get("status", "UNAVAILABLE")
    if safe_zones_status == "SAFE":
        safe_zone_subscore: Optional[float] = 94.0
    elif safe_zones_status == "MODERATE_RISK":
        safe_zone_subscore = 70.0
    elif safe_zones_status == "HIGH_RISK":
        safe_zone_subscore = 45.0
    else:
        safe_zone_subscore = None

    cta_strength = cta_intel.get("strength", "UNAVAILABLE")
    if cta_strength == "STRONG":
        cta_subscore: Optional[float] = 88.0
    elif cta_strength == "MODERATE":
        cta_subscore = 72.0
    elif cta_strength == "WEAK":
        cta_subscore = 45.0
    else:
        cta_subscore = None

    creative_quality_val = _reweighted_average([
        (hook_subscore, 0.25),
        (pacing_subscore, 0.25),
        (audio_subscore, 0.20),
        (safe_zone_subscore, 0.15),
        (cta_subscore, 0.15),
    ])
    creative_available = creative_quality_val is not None
    creative_quality_score = creative_quality_val if creative_available else 0.0

    # Derive visual contrast/brightness sub-score strictly from real frame telemetry
    avg_contrast = frame_tel.get("avg_contrast")
    avg_brightness = frame_tel.get("avg_brightness")
    lighting_quality = frame_tel.get("lighting_quality", "UNAVAILABLE")
    if avg_contrast is not None and has_visual_telemetry:
        contrast_score = round(min(96.0, max(35.0, 45.0 + float(avg_contrast))), 1)
        if lighting_quality == "OPTIMAL":
            contrast_score = round(min(98.0, contrast_score + 6.0), 1)
        elif lighting_quality in ("UNDEREXPOSED", "OVEREXPOSED"):
            contrast_score = round(max(30.0, contrast_score - 12.0), 1)
    else:
        contrast_score = None

    cuts_detected = pacing_intel.get("cuts_detected")
    avg_scene_sec = pacing_intel.get("avg_scene_duration_sec")
    wpm_val = audio_intel.get("words_per_minute")
    dead_air_cnt = audio_intel.get("dead_air_count")

    creative_components = [
        {
            "name": "Opening Hook Velocity",
            "score": hook_subscore if hook_subscore is not None else 0.0,
            "weight": 0.25,
            "status": compute_component_status(hook_subscore or 0.0, hook_subscore is not None),
            "details": (
                f"Based on opening cut timestamps {hook_intel.get('first_3s_cut_timestamps') or []} and frame contrast."
                if has_visual_telemetry
                else (
                    "Based solely on caption/title opening text (video frames not decoded)."
                    if topic["has_text"]
                    else "Unavailable: neither video frames nor caption text was provided."
                )
            ),
        },
        {
            "name": "Visual Pacing & Scene Boundaries",
            "score": pacing_subscore if pacing_subscore is not None else 0.0,
            "weight": 0.25,
            "status": compute_component_status(pacing_subscore or 0.0, pacing_subscore is not None),
            "details": (
                f"Detected {cuts_detected} cut(s) with avg {avg_scene_sec}s scene span across {duration:.1f}s."
                if (pacing_subscore is not None and duration is not None)
                else "Unavailable: video frames could not be decoded for cut detection."
            ),
        },
        {
            "name": "Vocal Cadence & Audio Energy",
            "score": audio_subscore if audio_subscore is not None else 0.0,
            "weight": 0.20,
            "status": compute_component_status(audio_subscore or 0.0, audio_subscore is not None),
            "details": (
                f"Measured {wpm_val} WPM with {dead_air_cnt} pause(s) >= 1.2s."
                if audio_available and wpm_val is not None
                else "Unavailable: speech audio track was not transcribed."
            ),
        },
        {
            "name": "Safe Zone UI Compliance",
            "score": safe_zone_subscore if safe_zone_subscore is not None else 0.0,
            "weight": 0.15,
            "status": compute_component_status(safe_zone_subscore or 0.0, safe_zone_subscore is not None),
            "details": safe_intel.get("guidelines", "Safe-zone pixel data unavailable."),
        },
        {
            "name": "CTA Text Clarity",
            "score": cta_subscore if cta_subscore is not None else 0.0,
            "weight": 0.15,
            "status": compute_component_status(cta_subscore or 0.0, cta_subscore is not None),
            "details": (
                f"Evaluated from {cta_intel.get('evaluated_from')}: {cta_intel.get('cta_type')}"
                + (f" (keywords: {', '.join(cta_intel.get('matched_keywords') or [])})" if cta_intel.get("matched_keywords") else ".")
            ),
        },
    ]

    creative_confidence = (
        0.78 if (stream_analyzed and audio_available)
        else (0.68 if stream_analyzed else (0.35 if is_simulated_video else (0.28 if creative_available else 0.0)))
    )
    creative_limitations_parts = []
    if is_simulated_video:
        creative_limitations_parts.append("Visual metrics are from sandbox sample simulation, not real video frames.")
    elif not stream_analyzed:
        creative_limitations_parts.append("Video frames were not decoded; duration, cuts, and safe zones could not be measured.")
    if not audio_available:
        creative_limitations_parts.append("Audio speech transcription is unavailable; spoken WPM and silent pauses were not measured.")

    creative_detail = {
        "score": creative_quality_score,
        "rating": compute_rating_label(creative_quality_score, creative_available),
        "confidence": creative_confidence,
        "score_type": "SIMULATED" if is_simulated_video else ("AI_ESTIMATE" if creative_available else "UNAVAILABLE"),
        "data_available": creative_available,
        "limitations": " ".join(creative_limitations_parts) or "Derived from decoded OpenCV frame telemetry and text metadata.",
        "methodology": "Weighted composite across available visual frame decoding, safe-zone pixel overlap, audio transcription (when available), and caption CTA signals.",
        "components": creative_components,
        "evidence_summary": (
            f"Decoded {sampled_frames} frame(s) ({resolution_str}, {fps_val} FPS, {duration:.2f}s) with {cuts_detected} cut(s)."
            if stream_analyzed and duration is not None
            else (
                "Simulated sandbox visual heuristics applied (not decoded pixels)."
                if is_simulated_video
                else (
                    f"Partial caption-only evaluation ({len(topic['keywords'])} topic keyword(s)); video pixels not decoded."
                    if creative_available
                    else "Insufficient data: no decoded video frames, audio transcript, or caption text."
                )
            )
        ),
    }

    # Dimension: Hook Strength
    first_3s_cut_bool = hook_intel.get("has_cut_in_first_3s")
    hook_cut_score = (90.0 if first_3s_cut_bool else 52.0) if first_3s_cut_bool is not None else None
    hook_text_score = (82.0 if topic["has_text"] and video_intel.get("text_context", {}).get("has_caption_hook_trigger") else (60.0 if topic["has_text"] else None))
    hook_available = hook_subscore is not None

    hook_detail = {
        "score": hook_subscore if hook_available else 0.0,
        "rating": compute_rating_label(hook_subscore or 0.0, hook_available),
        "confidence": 0.76 if stream_analyzed else (0.35 if is_simulated_video else (0.30 if hook_available else 0.0)),
        "score_type": "SIMULATED" if is_simulated_video else ("AI_ESTIMATE" if hook_available else "UNAVAILABLE"),
        "data_available": hook_available,
        "limitations": (
            "Audio opening speech not transcribed; relies on opening visual transitions and/or caption text."
            if not audio_available else "Evaluated from decoded frames and opening transcript."
        ),
        "methodology": "Evaluates visual transition density in 0-3.5s, opening frame luminance/contrast, and caption/title curiosity framing.",
        "components": [
            {
                "name": "First 3.5s Visual Cuts",
                "score": hook_cut_score if hook_cut_score is not None else 0.0,
                "weight": 0.40,
                "status": compute_component_status(hook_cut_score or 0.0, hook_cut_score is not None),
                "details": (
                    f"Cuts detected in first 3.5s at {hook_intel.get('first_3s_cut_timestamps') or []}."
                    if first_3s_cut_bool is not None
                    else "Unavailable: opening video frames were not decoded."
                ),
            },
            {
                "name": "Opening Frame Lighting & Contrast",
                "score": contrast_score if contrast_score is not None else 0.0,
                "weight": 0.35,
                "status": compute_component_status(contrast_score or 0.0, contrast_score is not None),
                "details": (
                    f"Measured lighting={lighting_quality} (brightness={avg_brightness}, contrast={avg_contrast})."
                    if contrast_score is not None
                    else "Unavailable: opening frame pixels were not decoded."
                ),
            },
            {
                "name": "Caption / Title Hook Trigger",
                "score": hook_text_score if hook_text_score is not None else 0.0,
                "weight": 0.25,
                "status": compute_component_status(hook_text_score or 0.0, hook_text_score is not None),
                "details": (
                    f"Found curiosity trigger(s): {', '.join(hook_intel.get('caption_hook_triggers') or []) or 'none'} in '{topic['opening_line'][:60]}'."
                    if topic["has_text"]
                    else "Unavailable: no caption, title, or speech transcript supplied."
                ),
            },
        ],
        "evidence_summary": (
            f"Opening hook scored {hook_subscore:.1f}/100"
            + (f" across {sampled_frames} decoded frame(s)." if stream_analyzed else " (partial text/simulation heuristic; frames not decoded).")
            if hook_available
            else "Hook strength unavailable without decoded video frames or caption/transcript text."
        ),
    }

    # Dimension: Editing and Pacing
    static_ratio = pacing_intel.get("static_visual_ratio")
    stagnation_score = (
        max(20.0, round(100.0 - (float(static_ratio) * 180.0), 1))
        if static_ratio is not None and has_visual_telemetry
        else None
    )
    dead_air_score = (
        (95.0 if (dead_air_cnt or 0) == 0 else 65.0)
        if audio_available and dead_air_cnt is not None
        else None
    )
    pacing_available = pacing_subscore is not None

    pacing_detail = {
        "score": pacing_subscore if pacing_available else 0.0,
        "rating": compute_rating_label(pacing_subscore or 0.0, pacing_available),
        "confidence": 0.85 if stream_analyzed else (0.35 if is_simulated_video else 0.0),
        "score_type": "SIMULATED" if is_simulated_video else ("AI_ESTIMATE" if stream_analyzed else "UNAVAILABLE"),
        "data_available": pacing_available,
        "limitations": (
            "Audio pause timing not measured (no speech transcription)."
            if stream_analyzed and not audio_available
            else ("Unavailable: video frames could not be decoded." if not pacing_available else "Simulated sandbox pacing.")
        ),
        "methodology": "Measures histogram cut transitions, inter-frame pixel motion delta, and audio dead-air pauses when available.",
        "components": [
            {
                "name": "Cut Density & Rhythm",
                "score": pacing_subscore if pacing_subscore is not None else 0.0,
                "weight": 0.50,
                "status": compute_component_status(pacing_subscore or 0.0, pacing_subscore is not None),
                "details": (
                    f"{cuts_detected} scene cut(s) detected; average shot length {avg_scene_sec}s."
                    if pacing_available
                    else "Unavailable: video frames not decoded."
                ),
            },
            {
                "name": "Visual Stagnation Avoidance",
                "score": stagnation_score if stagnation_score is not None else 0.0,
                "weight": 0.30,
                "status": compute_component_status(stagnation_score or 0.0, stagnation_score is not None),
                "details": (
                    f"Low-motion frame ratio: {round(float(static_ratio) * 100, 1)}% ({len(frame_tel.get('static_segments') or [])} static window(s) >= 2s)."
                    if stagnation_score is not None
                    else "Unavailable: frame motion telemetry not decoded."
                ),
            },
            {
                "name": "Dead Air Audio Trimming",
                "score": dead_air_score if dead_air_score is not None else 0.0,
                "weight": 0.20,
                "status": compute_component_status(dead_air_score or 0.0, dead_air_score is not None),
                "details": (
                    f"{dead_air_cnt} pause(s) exceeding 1.2s detected."
                    if dead_air_score is not None
                    else "Unavailable: speech/audio track not decoded."
                ),
            },
        ],
        "evidence_summary": (
            f"Editing rated {pacing_intel.get('pacing_label')} ({cuts_detected} cut(s), avg {avg_scene_sec}s/shot)."
            if stream_analyzed
            else ("Sandbox simulated pacing rhythm." if is_simulated_video else "Visual editing pacing unavailable without decoded video frames.")
        ),
    }

    # Dimension: Content Clarity
    sub_readability = safe_intel.get("subtitle_readability_score")
    sub_readability_val = float(sub_readability) if sub_readability is not None else None
    clarity_val = _reweighted_average([
        (audio_subscore, 0.40),
        (sub_readability_val, 0.35),
        (safe_zone_subscore, 0.25),
    ])
    clarity_available = clarity_val is not None

    clarity_detail = {
        "score": clarity_val if clarity_available else 0.0,
        "rating": compute_rating_label(clarity_val or 0.0, clarity_available),
        "confidence": 0.72 if stream_analyzed else (0.35 if is_simulated_video else 0.0),
        "score_type": "SIMULATED" if is_simulated_video else ("AI_ESTIMATE" if stream_analyzed else "UNAVAILABLE"),
        "data_available": clarity_available,
        "limitations": (
            "Audio articulation/WPM unavailable without speech transcription; score reflects visual safe-zone & text-contour readability only."
            if clarity_available and not audio_available
            else ("Video frames and audio unavailable." if not clarity_available else "Grounded in visual + audio inputs.")
        ),
        "methodology": "Evaluates UI margin edge/text overlap across bottom 22% / right 18% safe zones and vocal clarity when transcribed.",
        "components": [
            {
                "name": "Spoken Audio & Vocal Articulation",
                "score": audio_subscore if audio_subscore is not None else 0.0,
                "weight": 0.40,
                "status": compute_component_status(audio_subscore or 0.0, audio_subscore is not None),
                "details": f"{wpm_val} WPM" if wpm_val is not None else "Unavailable: audio track not transcribed.",
            },
            {
                "name": "Lower/Right Margin Readability",
                "score": sub_readability_val if sub_readability_val is not None else 0.0,
                "weight": 0.35,
                "status": compute_component_status(sub_readability_val or 0.0, sub_readability_val is not None),
                "details": (
                    f"Estimated readability {sub_readability_val}/100 (safe-zone hazard events: {len(safe_intel.get('hazard_events') or [])})."
                    if sub_readability_val is not None
                    else "Unavailable: video frames not decoded."
                ),
            },
            {
                "name": "Instagram UI Safe Margin Clearance",
                "score": safe_zone_subscore if safe_zone_subscore is not None else 0.0,
                "weight": 0.25,
                "status": compute_component_status(safe_zone_subscore or 0.0, safe_zone_subscore is not None),
                "details": safe_intel.get("guidelines", "Safe margins unavailable."),
            },
        ],
        "evidence_summary": (
            f"Safe-zone inspection across {sampled_frames} frame(s) rated {safe_zones_status}."
            if stream_analyzed
            else ("Sandbox simulated safe-zone score." if is_simulated_video else "Visual clarity metrics unavailable.")
        ),
    }

    # Dimension: CTA Effectiveness
    cta_available = cta_subscore is not None
    cta_detail = {
        "score": cta_subscore if cta_available else 0.0,
        "rating": compute_rating_label(cta_subscore or 0.0, cta_available),
        "confidence": 0.60 if cta_available and not audio_available else (0.85 if cta_available else 0.0),
        "score_type": "AI_ESTIMATE" if cta_available else "UNAVAILABLE",
        "data_available": cta_available,
        "limitations": (
            "Evaluated from caption/title text only; spoken closing CTA in audio requires transcription."
            if cta_available and not audio_available
            else ("Unavailable: no caption, title, or transcript provided." if not cta_available else "")
        ),
        "methodology": "Checks caption/title and transcript (when present) for explicit audience prompts (comment, save, share, link/DM).",
        "components": [
            {
                "name": "CTA Specificity & Keyword Alignment",
                "score": cta_subscore if cta_available else 0.0,
                "weight": 1.0,
                "status": compute_component_status(cta_subscore or 0.0, cta_available),
                "details": (
                    f"Detected {cta_intel.get('cta_type')} ({', '.join(cta_intel.get('matched_keywords') or []) or 'no action verb matched'})."
                    if cta_available
                    else "Unavailable: no caption or spoken transcript text provided."
                ),
            }
        ],
        "evidence_summary": (
            f"Caption CTA classified as {cta_intel.get('cta_type')} ({cta_strength})."
            if cta_available
            else "No caption or audio transcript supplied to verify CTA presence."
        ),
    }

    # --------------------------------------------------------------------------
    # 2. Performance Score (Never fabricate defaults when metrics are missing)
    # --------------------------------------------------------------------------
    er_metric = performance_metrics.get("engagement_rate") or {}
    bm_metric = performance_metrics.get("benchmark_delta") or {}
    like_metric = performance_metrics.get("like_rate_views") or {}

    er_val = er_metric.get("value")
    er_score = min(100.0, max(20.0, round((er_val / 0.08) * 80.0, 1))) if er_val is not None else None

    bm_delta_val = bm_metric.get("value")
    delta_score = min(100.0, max(20.0, round(70.0 + (bm_delta_val * 0.5), 1))) if bm_delta_val is not None else None

    like_val = like_metric.get("value")
    like_score = min(100.0, max(20.0, round((like_val / 0.06) * 80.0, 1))) if like_val is not None else None

    perf_score_val = _reweighted_average([
        (er_score, 0.40),
        (delta_score, 0.35),
        (like_score, 0.25),
    ])
    perf_available = perf_score_val is not None
    perf_score = perf_score_val if perf_available else 0.0

    available_perf_inputs = sum(1 for v in (er_score, delta_score, like_score) if v is not None)
    perf_confidence = (
        0.0 if not perf_available
        else (0.35 if is_simulated_metrics else round(0.55 + (0.12 * available_perf_inputs), 2))
    )

    perf_detail = {
        "score": perf_score,
        "rating": compute_rating_label(perf_score, perf_available),
        "confidence": perf_confidence,
        "score_type": (
            "UNAVAILABLE" if not perf_available
            else ("SIMULATED" if is_simulated_metrics else ("CALCULATED_FROM_MEASURED" if is_connected else "AI_ESTIMATE"))
        ),
        "data_available": perf_available,
        "limitations": (
            "Sandbox simulation demo numbers (not real Instagram insights)."
            if is_simulated_metrics
            else (
                "No post-publish views, reach, or engagement metrics were available for this Reel."
                if not perf_available
                else (
                    "Account 30-day baseline or breakdown counts incomplete; score reweighted over available metrics."
                    if available_perf_inputs < 3
                    else "Computed from measured Meta/declared engagement ratios."
                )
            )
        ),
        "methodology": "Reweighted comparison of available measured engagement and view ratios (omits unavailable ratios rather than guessing).",
        "components": [
            {
                "name": "Aggregate Engagement Rate",
                "score": er_score if er_score is not None else 0.0,
                "weight": 0.40,
                "status": compute_component_status(er_score or 0.0, er_score is not None),
                "details": f"{er_metric.get('formatted', 'N/A')} ({er_metric.get('source', 'Unavailable')})",
            },
            {
                "name": "Account Baseline Velocity",
                "score": delta_score if delta_score is not None else 0.0,
                "weight": 0.35,
                "status": compute_component_status(delta_score or 0.0, delta_score is not None),
                "details": f"{bm_metric.get('formatted', 'N/A')} ({bm_metric.get('limitations', 'Unavailable')})",
            },
            {
                "name": "Audience Like Propensity",
                "score": like_score if like_score is not None else 0.0,
                "weight": 0.25,
                "status": compute_component_status(like_score or 0.0, like_score is not None),
                "details": f"{like_metric.get('formatted', 'N/A')} ({like_metric.get('source', 'Unavailable')})",
            },
        ],
        "evidence_summary": (
            f"Views: {performance_metrics.get('views', {}).get('formatted', 'N/A')}, "
            f"Engagement: {er_metric.get('formatted', 'N/A')}."
            if perf_available
            else "Performance metrics are unavailable (no views, reach, or interactions data)."
        ),
    }

    # --------------------------------------------------------------------------
    # 3. Growth Conversion Score
    # --------------------------------------------------------------------------
    save_metric = performance_metrics.get("save_rate") or {}
    share_metric = performance_metrics.get("share_rate") or {}
    save_val = save_metric.get("value")
    share_val = share_metric.get("value")

    save_score = min(100.0, max(20.0, round((save_val / 0.03) * 80.0, 1))) if save_val is not None else None
    share_score = min(100.0, max(20.0, round((share_val / 0.02) * 80.0, 1))) if share_val is not None else None

    # Do not report growth conversion when both save_rate AND share_rate are unavailable
    has_any_growth_metric = (save_score is not None) or (share_score is not None)
    growth_val = (
        _reweighted_average([
            (save_score, 0.35),
            (share_score, 0.35),
            (cta_subscore, 0.30),
        ])
        if has_any_growth_metric
        else None
    )
    growth_available = growth_val is not None
    growth_score = growth_val if growth_available else 0.0

    growth_confidence = (
        0.0 if not growth_available
        else (0.35 if is_simulated_metrics else (0.85 if (save_score is not None and share_score is not None) else 0.55))
    )

    growth_detail = {
        "score": growth_score,
        "rating": compute_rating_label(growth_score, growth_available),
        "confidence": growth_confidence,
        "score_type": (
            "UNAVAILABLE" if not growth_available
            else ("SIMULATED" if is_simulated_metrics else "CALCULATED_FROM_MEASURED")
        ),
        "data_available": growth_available,
        "limitations": (
            "Sandbox simulation demo numbers (not real Instagram saves/shares)."
            if is_simulated_metrics
            else (
                "Save and share metrics are unavailable for this Reel; growth conversion cannot be calculated."
                if not growth_available
                else "Based on measured save/share ratios and CTA alignment."
            )
        ),
        "methodology": "Evaluates high-intent save rate, share rate, and explicit CTA clarity when conversion metrics exist.",
        "components": [
            {
                "name": "Save / Bookmark Density",
                "score": save_score if save_score is not None else 0.0,
                "weight": 0.35,
                "status": compute_component_status(save_score or 0.0, save_score is not None),
                "details": f"Save rate: {save_metric.get('formatted', 'N/A')} ({save_metric.get('source', 'Unavailable')})",
            },
            {
                "name": "Share / DM Advocacy",
                "score": share_score if share_score is not None else 0.0,
                "weight": 0.35,
                "status": compute_component_status(share_score or 0.0, share_score is not None),
                "details": f"Share rate: {share_metric.get('formatted', 'N/A')} ({share_metric.get('source', 'Unavailable')})",
            },
            {
                "name": "Call-to-Action Clarity",
                "score": cta_subscore if cta_available else 0.0,
                "weight": 0.30,
                "status": compute_component_status(cta_subscore or 0.0, cta_available),
                "details": f"CTA classification: {cta_intel.get('cta_type', 'UNAVAILABLE')}",
            },
        ],
        "evidence_summary": (
            f"Save rate {save_metric.get('formatted', 'N/A')}, Share rate {share_metric.get('formatted', 'N/A')}."
            if has_any_growth_metric
            else "Save and share counts are unavailable; growth conversion score is marked Unavailable rather than estimated."
        ),
    }

    # --------------------------------------------------------------------------
    # 4. Viral Potential Estimate (Strictly distinguishes real watch telemetry vs missing retention)
    # --------------------------------------------------------------------------
    watch_metric = performance_metrics.get("watch_ratio") or {}
    watch_ratio_val = watch_metric.get("value")
    watch_score = (
        min(100.0, max(20.0, round((watch_ratio_val / 0.65) * 80.0, 1)))
        if watch_ratio_val is not None
        else None
    )

    viral_val = _reweighted_average([
        (share_score, 0.40),
        (hook_subscore, 0.35),
        (watch_score, 0.25),
    ])
    viral_available = viral_val is not None
    viral_score = viral_val if viral_available else 0.0

    viral_conf_components = sum(1 for x in (share_score, hook_subscore, watch_score) if x is not None)
    viral_confidence = (
        0.0 if not viral_available
        else (0.35 if is_simulated else round(0.25 + (0.20 * viral_conf_components), 2))
    )

    viral_detail = {
        "score": viral_score,
        "rating": compute_rating_label(viral_score, viral_available),
        "confidence": viral_confidence,
        "score_type": "UNAVAILABLE" if not viral_available else ("SIMULATED" if is_simulated else "AI_ESTIMATE"),
        "data_available": viral_available,
        "limitations": (
            "Sandbox simulation demo inputs (not live reach/shares)."
            if is_simulated
            else (
                "Timestamped retention / watch-time data is unavailable; viral potential is an AI estimate excluding measured retention."
                if not timestamped_retention_available
                else "Estimated from measured shares, hook telemetry, and watch-time telemetry."
            )
        ),
        "methodology": "AI estimate combining share rate (when available), opening hook signals, and measured watch-time ratio (omitted when unavailable).",
        "components": [
            {
                "name": "Share Propensity",
                "score": share_score if share_score is not None else 0.0,
                "weight": 0.40,
                "status": compute_component_status(share_score or 0.0, share_score is not None),
                "details": f"Share rate: {share_metric.get('formatted', 'N/A')}",
            },
            {
                "name": "Opening Hook Signals",
                "score": hook_subscore if hook_subscore is not None else 0.0,
                "weight": 0.35,
                "status": compute_component_status(hook_subscore or 0.0, hook_subscore is not None),
                "details": hook_detail["evidence_summary"],
            },
            {
                "name": "Watch-Time / Retention Signal",
                "score": watch_score if watch_score is not None else 0.0,
                "weight": 0.25,
                "status": compute_component_status(watch_score or 0.0, watch_score is not None),
                "details": (
                    f"Average watch ratio: {watch_metric.get('formatted')} (summary average; timestamped retention curve available={timestamped_retention_available})."
                    if watch_score is not None
                    else "Unavailable: no watch-time or retention data was provided by Meta or local telemetry."
                ),
            },
        ],
        "evidence_summary": (
            f"AI viral estimate {viral_score:.1f}/100 (retention measured: {timestamped_retention_available})."
            if viral_available
            else "Insufficient hook, share, or watch telemetry to estimate viral potential."
        ),
    }

    scores = {
        "creative_quality": creative_detail,
        "hook_strength": hook_detail,
        "editing_and_pacing": pacing_detail,
        "content_clarity": clarity_detail,
        "cta_effectiveness": cta_detail,
        "performance": perf_detail,
        "performance_insights": perf_detail,
        "growth_conversion": growth_detail,
        "growth_and_conversion": growth_detail,
        "viral_potential": viral_detail,
    }

    # --------------------------------------------------------------------------
    # 5. Grounded Timestamped Video Timeline Findings (Strictly Derived from Real Frames/Text)
    # --------------------------------------------------------------------------
    timeline_findings: List[Dict[str, Any]] = []
    frame_obs = frame_tel.get("frame_observations") or []
    cut_times = pacing_intel.get("cut_timestamps") or []
    static_segs = frame_tel.get("static_segments") or []
    hazard_events = safe_intel.get("hazard_events") or []

    if stream_analyzed and duration is not None:
        first_frame = frame_obs[0] if frame_obs else {}
        hook_end = round(min(3.0, duration), 2)
        first_cuts = hook_intel.get("first_3s_cut_timestamps") or []
        f0_b = first_frame.get("brightness", avg_brightness)
        f0_c = first_frame.get("contrast", avg_contrast)

        timeline_findings.append({
            "id": str(uuid.uuid4()),
            "timestamp_start_seconds": 0.0,
            "timestamp_end_seconds": hook_end,
            "time_range_formatted": f"00:00 - {_fmt_sec(hook_end)}",
            "category": "HOOK",
            "severity": "STRENGTH" if (len(first_cuts) > 0 and lighting_quality == "OPTIMAL") else "OPPORTUNITY",
            "observation": (
                f"Opening frame at 0.00s decoded at {resolution_str} ({aspect_ratio}, {fps_val} FPS) with {len(first_cuts)} scene cut(s) in the first 3.5s."
            ),
            "evidence": (
                f"Frame 0 luma={f0_b}, contrast={f0_c}, lighting={lighting_quality}; early cuts at {first_cuts or 'none'}."
                + (f" Opening caption text: '{topic['opening_line'][:70]}'." if topic["opening_line"] else " No caption text supplied.")
            ),
            "recommendation": (
                "Retain early visual change while tightening opening caption hook."
                if len(first_cuts) > 0
                else "Add a visual cut, framing punch-in, or high-contrast visual reset before 2.5s to reduce early swipe-away."
            ),
            "proposed_edit": (
                f"Review thumbnail frame at 0.00s and insert a cut or 1.15x scale transition near {round(min(2.0, duration * 0.5), 1)}s."
                if len(first_cuts) == 0
                else f"Keep early cut timing around {first_cuts[0]}s and ensure crisp lighting (current luma={f0_b})."
            ),
            "is_heuristic_risk": True,
            "confidence": 0.85,
            "limitations": "Audio speech track not transcribed; hook verdict reflects visual pixels and caption only.",
            "source": "FRAME_PIXEL_ANALYSIS",
        })

        # Static segments OR actual cut timestamps
        if static_segs:
            for seg in static_segs[:2]:
                s_start = float(seg["start"])
                s_end = float(seg["end"])
                timeline_findings.append({
                    "id": str(uuid.uuid4()),
                    "timestamp_start_seconds": s_start,
                    "timestamp_end_seconds": s_end,
                    "time_range_formatted": f"{_fmt_sec(s_start)} - {_fmt_sec(s_end)}",
                    "category": "PACING",
                    "severity": "WARNING",
                    "observation": f"Low inter-frame pixel motion detected for {seg['duration']}s ({s_start}s to {s_end}s).",
                    "evidence": f"Measured inter-frame pixel diff averaged {seg['avg_motion']} (< 2.0 threshold) across frames in this interval.",
                    "recommendation": "Break up this static visual stretch with a framing punch-in, B-roll cutaway, or on-screen callout.",
                    "proposed_edit": f"Insert a visual change or B-roll overlay starting around {s_start}s.",
                    "is_heuristic_risk": False,
                    "confidence": 0.88,
                    "limitations": "Motion measured via frame-to-frame luma delta; subtle eye movement may fall below 2.0 threshold.",
                    "source": "FRAME_PIXEL_ANALYSIS",
                })
        elif cut_times:
            c_start = round(cut_times[0], 2)
            c_end = round(cut_times[-1], 2)
            timeline_findings.append({
                "id": str(uuid.uuid4()),
                "timestamp_start_seconds": c_start,
                "timestamp_end_seconds": c_end,
                "time_range_formatted": f"{_fmt_sec(c_start)} - {_fmt_sec(c_end)}",
                "category": "PACING",
                "severity": "STRENGTH" if pacing_intel.get("pacing_label") in ("FAST", "BALANCED") else "OPPORTUNITY",
                "observation": f"Detected {len(cut_times)} visual scene transition(s) across {duration:.1f}s (avg {avg_scene_sec}s per segment).",
                "evidence": f"Histogram correlation drops (<0.65) recorded at timestamps: {', '.join(f'{t}s' for t in cut_times[:8])}.",
                "recommendation": "Align spoken sentences or caption reveals cleanly to these measured visual cut beats.",
                "proposed_edit": f"Verify transitions near {cut_times[0]}s sit cleanly on phrasing boundaries.",
                "is_heuristic_risk": False,
                "confidence": 0.86,
                "limitations": "Cut detection samples frames at timeline intervals; rapid flash cuts within one interval may merge.",
                "source": "FRAME_PIXEL_ANALYSIS",
            })
        else:
            timeline_findings.append({
                "id": str(uuid.uuid4()),
                "timestamp_start_seconds": 0.0,
                "timestamp_end_seconds": duration,
                "time_range_formatted": f"00:00 - {_fmt_sec(duration)}",
                "category": "PACING",
                "severity": "INFO" if duration <= 3.0 else "WARNING",
                "observation": f"Single continuous shot with 0 scene cuts detected across {duration:.2f}s ({sampled_frames} sampled frame(s)).",
                "evidence": f"Color histogram correlation stayed >= 0.65 across all {sampled_frames} sampled frames.",
                "recommendation": "If clip > 5s, add at least one framing switch or B-roll overlay to keep visual momentum.",
                "proposed_edit": f"Consider a 110%-115% zoom cut near {round(duration * 0.5, 1)}s if longer format." if duration > 3.0 else "Clip duration under 3s; single shot is expected.",
                "is_heuristic_risk": True,
                "confidence": 0.84,
                "limitations": "Sampled frame-level color histogram check.",
                "source": "FRAME_PIXEL_ANALYSIS",
            })

        # Safe zone check
        if hazard_events:
            first_ev = hazard_events[0]
            last_ev = hazard_events[-1]
            ev_ts = ", ".join(f"{e['timestamp_sec']}s" for e in hazard_events[:5])
            zones_seen = sorted({z for e in hazard_events for z in e.get("zones", [])})
            timeline_findings.append({
                "id": str(uuid.uuid4()),
                "timestamp_start_seconds": float(first_ev["timestamp_sec"]),
                "timestamp_end_seconds": float(last_ev["timestamp_sec"]),
                "time_range_formatted": f"{_fmt_sec(first_ev['timestamp_sec'])} - {_fmt_sec(last_ev['timestamp_sec'])}",
                "category": "VISUAL_CLARITY",
                "severity": "WARNING" if safe_zones_status == "HIGH_RISK" else "OPPORTUNITY",
                "observation": f"Visual edges/text contours detected inside Instagram UI overlay margins at {len(hazard_events)} timestamp(s).",
                "evidence": f"Zones triggered ({', '.join(zones_seen)}) at {ev_ts}; bottom edge energy={first_ev.get('bottom_edge_energy')}.",
                "recommendation": "Keep burned-in captions and primary subjects above the bottom 22% and left of the right 18% icon rail.",
                "proposed_edit": f"Inspect frame(s) around {first_ev['timestamp_sec']}s and move lower text higher into vertical center (Y=35%-65%).",
                "is_heuristic_risk": False,
                "confidence": 0.82,
                "limitations": "Edge/gradient contours in lower/right regions detect high-contrast scene details as well as burned-in text.",
                "source": "FRAME_PIXEL_ANALYSIS",
            })
        else:
            timeline_findings.append({
                "id": str(uuid.uuid4()),
                "timestamp_start_seconds": 0.0,
                "timestamp_end_seconds": duration,
                "time_range_formatted": f"00:00 - {_fmt_sec(duration)}",
                "category": "VISUAL_CLARITY",
                "severity": "STRENGTH",
                "observation": f"Bottom 22% and right 18% UI overlay zones remained clear across {sampled_frames} sampled frame(s).",
                "evidence": "Edge density and morphological text-line checks stayed within Instagram 9:16 safe thresholds.",
                "recommendation": "Maintain safe vertical margins for subtitles and titles.",
                "proposed_edit": f"Aspect ratio {aspect_ratio} ({resolution_str}) framing verified.",
                "is_heuristic_risk": False,
                "confidence": 0.82,
                "limitations": "Verified only on sampled frames.",
                "source": "FRAME_PIXEL_ANALYSIS",
            })
    elif is_simulated_video and duration is not None:
        timeline_findings.append({
            "id": str(uuid.uuid4()),
            "timestamp_start_seconds": 0.0,
            "timestamp_end_seconds": min(3.0, duration),
            "time_range_formatted": f"00:00 - {_fmt_sec(min(3.0, duration))}",
            "category": "HOOK",
            "severity": "INFO",
            "observation": "Sandbox simulation hook placeholder (video frames were not decoded locally).",
            "evidence": (
                f"Simulated timeline based on sandbox caption: '{topic['opening_line'][:70]}'."
                if topic["opening_line"]
                else "Simulated deterministic sandbox sample."
            ),
            "recommendation": "Upload a real MP4/MOV draft or connect a live Instagram video asset for frame-exact diagnostics.",
            "proposed_edit": "N/A (Sandbox Simulation Mode)",
            "is_heuristic_risk": True,
            "confidence": 0.30,
            "limitations": "Simulated demo data — not decoded from real video pixels.",
            "source": "SANDBOX_SIMULATED",
        })
        timeline_findings.append({
            "id": str(uuid.uuid4()),
            "timestamp_start_seconds": 0.0,
            "timestamp_end_seconds": duration,
            "time_range_formatted": f"00:00 - {_fmt_sec(duration)}",
            "category": "PACING",
            "severity": "INFO",
            "observation": f"Sandbox demo pacing estimate: {cuts_detected} simulated cut(s) across {duration:.1f}s.",
            "evidence": "Deterministic sandbox catalog approximation; real pixels not analyzed.",
            "recommendation": "Use Video Upload mode for real frame-accurate cut timestamps.",
            "proposed_edit": "N/A (Sandbox Simulation Mode)",
            "is_heuristic_risk": True,
            "confidence": 0.25,
            "limitations": "Simulated demo timeline — not live Instagram data.",
            "source": "SANDBOX_SIMULATED",
        })
    else:
        timeline_findings.append({
            "id": str(uuid.uuid4()),
            "timestamp_start_seconds": 0.0,
            "timestamp_end_seconds": 0.0,
            "time_range_formatted": "Stream Unavailable",
            "category": "VISUAL_CLARITY",
            "severity": "INFO",
            "observation": "Video stream bytes could not be decoded locally; frame-level timestamps, resolution, FPS, and cuts are unavailable.",
            "evidence": meta.get("limitation") or "Only URL or metadata was accessible without downloadable video stream.",
            "recommendation": "Upload the video file directly in Mode B for frame-accurate cut, lighting, and safe-zone analysis.",
            "proposed_edit": "Upload .mp4/.mov file to enable pixel & timestamp diagnostics.",
            "is_heuristic_risk": False,
            "confidence": 1.0,
            "limitations": "No decoded frames available.",
            "source": "STREAM_UNAVAILABLE",
        })
        timeline_findings.append({
            "id": str(uuid.uuid4()),
            "timestamp_start_seconds": 0.0,
            "timestamp_end_seconds": 3.0,
            "time_range_formatted": "00:00 - 00:03 (Copy)",
            "category": "HOOK",
            "severity": "STRENGTH" if topic["has_text"] and hook_intel.get("caption_hook_triggers") else "OPPORTUNITY",
            "observation": (
                f"Evaluated Reel opening copy from caption/title: '{topic['opening_line'][:80]}'."
                if topic["has_text"]
                else "No opening video frames or caption text were available to score the 0-3s hook."
            ),
            "evidence": (
                f"Detected hook triggers: {', '.join(hook_intel.get('caption_hook_triggers') or []) or 'none'}."
                if topic["has_text"]
                else "Neither video frames nor caption text present."
            ),
            "recommendation": "Lead the caption and opening 3s visual overlay with an immediate outcome or question tied to the core topic.",
            "proposed_edit": f"Refine opening line around '{topic['topic_phrase'] or 'your core takeaway'}'.",
            "is_heuristic_risk": True,
            "confidence": 0.35 if topic["has_text"] else 0.0,
            "limitations": "Video frames & spoken audio not decoded.",
            "source": "CAPTION_HEURISTIC" if topic["has_text"] else "STREAM_UNAVAILABLE",
        })

    # Audio speech finding (real pauses ONLY if transcribed; explicit unavailable notice otherwise)
    dead_airs = audio_intel.get("dead_air_intervals") or []
    if audio_available and dead_airs:
        for da in dead_airs[:3]:
            timeline_findings.append({
                "id": str(uuid.uuid4()),
                "timestamp_start_seconds": float(da.get("start", 0.0)),
                "timestamp_end_seconds": float(da.get("end", 0.0)),
                "time_range_formatted": f"{_fmt_sec(da.get('start', 0.0))} - {_fmt_sec(da.get('end', 0.0))}",
                "category": "AUDIO_SPEECH",
                "severity": "WARNING",
                "observation": f"Vocal pause of {da.get('duration')}s detected in supplied audio telemetry.",
                "evidence": da.get("risk", "Extended pause in spoken delivery."),
                "recommendation": "Tighten silence gaps if unintended.",
                "proposed_edit": f"Trim gap from {da.get('start')}s to {da.get('end')}s.",
                "is_heuristic_risk": False,
                "confidence": 0.85,
                "limitations": "Derived from supplied pause telemetry/transcript.",
                "source": "AUDIO_TELEMETRY",
            })
    elif not audio_available:
        audio_end = duration if duration is not None else 0.0
        timeline_findings.append({
            "id": str(uuid.uuid4()),
            "timestamp_start_seconds": 0.0,
            "timestamp_end_seconds": audio_end,
            "time_range_formatted": f"00:00 - {_fmt_sec(audio_end)}" if duration is not None else "Audio Unavailable",
            "category": "AUDIO_SPEECH",
            "severity": "INFO",
            "observation": "Spoken audio track could not be transcribed; WPM and audio dead-air pauses were not measured.",
            "evidence": audio_intel.get("pacing_verdict", "No ASR/audio decoder installed."),
            "recommendation": "Ensure spoken hook and CTA match your on-screen captions.",
            "proposed_edit": "Verify manually that silences > 1.2s are trimmed in your editor.",
            "is_heuristic_risk": False,
            "confidence": 1.0,
            "limitations": "Speech audio is unmeasured.",
            "source": "AUDIO_UNAVAILABLE",
        })

    # Closing CTA Finding (always grounded in real caption/title or marked unverified)
    cta_start = round(max(0.0, duration - 4.0), 2) if duration is not None else 0.0
    cta_end = round(duration, 2) if duration is not None else 0.0
    timeline_findings.append({
        "id": str(uuid.uuid4()),
        "timestamp_start_seconds": cta_start,
        "timestamp_end_seconds": cta_end,
        "time_range_formatted": f"{_fmt_sec(cta_start)} - {_fmt_sec(cta_end)}" if duration is not None else "Closing / Caption CTA",
        "category": "CTA",
        "severity": "STRENGTH" if cta_strength == "STRONG" else ("OPPORTUNITY" if topic["has_text"] else "INFO"),
        "observation": (
            f"Caption/title CTA analysis classified trigger as {cta_intel.get('cta_type')}."
            if topic["has_text"]
            else "No caption or speech transcript supplied; closing CTA could not be verified."
        ),
        "evidence": (
            f"Matched CTA keyword(s): {', '.join(cta_intel.get('matched_keywords') or []) or 'none'} in caption/title."
            if topic["has_text"]
            else "Audio speech and caption text unavailable."
        ),
        "recommendation": (
            f"Keep the clear CTA around '{topic['topic_phrase'] or 'this Reel'}' and reinforce visually in the final 3 seconds."
            if cta_strength == "STRONG"
            else f"Add one explicit keyword or save CTA tied to '{topic['topic_phrase'] or 'your Reel topic'}'."
        ),
        "proposed_edit": (
            f"Add final overlay CTA specific to {topic['topic_phrase'] or 'your Reel takeaway'}."
        ),
        "is_heuristic_risk": not cta_available,
        "confidence": 0.65 if cta_available else 0.0,
        "limitations": "Based on caption/title text; audio speech CTA requires spoken transcription.",
        "source": "CAPTION_HEURISTIC" if topic["has_text"] else "AUDIO_UNAVAILABLE",
    })

    # --------------------------------------------------------------------------
    # 6. Prioritized Action Plan (Strictly grounded in measured telemetry & actual topic)
    # --------------------------------------------------------------------------
    topic_label = topic["topic_phrase"] or (f"uploaded draft ({topic['filename_hint']})" if topic["filename_hint"] else "this Reel")
    views_fmt = performance_metrics.get("views", {}).get("formatted", "N/A")
    comment_rate_fmt = performance_metrics.get("comment_rate", {}).get("formatted", "N/A")
    save_rate_fmt = performance_metrics.get("save_rate", {}).get("formatted", "N/A")
    share_rate_fmt = performance_metrics.get("share_rate", {}).get("formatted", "N/A")

    action_plan = [
        {
            "priority": 1,
            "area": f"Opening Hook ({topic_label})",
            "what_worked": (
                f"Opening frame decoded at {resolution_str} with {lighting_quality.lower()} lighting (brightness {avg_brightness}, contrast {avg_contrast})."
                if stream_analyzed
                else (f"Opening copy provided: '{topic['opening_line'][:70]}'." if topic["opening_line"] else "Hook awaits video/copy context.")
            ),
            "what_underperformed": (
                "No visual cut detected within the first 3.5 seconds."
                if first_3s_cut_bool is False
                else (
                    "Opening frame/hook text lacks an explicit curiosity question or problem hook trigger."
                    if not (hook_intel.get("caption_hook_triggers") or [])
                    else "Audio hook delivery could not be transcribed for verbal clarity scoring."
                )
            ),
            "why_it_happened": (
                "When visual framing stays fixed in 0-3s without a framing or text change, feed scrollers swipe faster."
                if stream_analyzed
                else "Video pixels or spoken transcript were unavailable for full 0-3s hook inspection."
            ),
            "supporting_evidence": (
                f"Hook score: {hook_subscore}/100; 0-3.5s cuts: {hook_intel.get('first_3s_cut_timestamps') or []}; caption triggers: {hook_intel.get('caption_hook_triggers') or []}."
                if hook_subscore is not None
                else "Hook telemetry partially unavailable (no decoded stream or caption)."
            ),
            "what_to_change": (
                f"Lead '{topic_label}' immediately with its core payoff or question in frame 0 text and add a visual cut within 2.5s."
            ),
            "how_to_implement": (
                f"Place a centered 5-7 word headline referencing '{topic_label}' in the top-middle safe zone"
                + (f" and tighten opening motion before {round(min(2.5, duration), 1)}s." if duration else ".")
            ),
            "follow_up_test_metric": f"Monitor early plays/views (currently {views_fmt}) and 3-second retention once published.",
            "confidence": hook_detail["confidence"],
            "limitations": hook_detail["limitations"],
        },
        {
            "priority": 2,
            "area": "Visual Pacing & UI Safe Margins",
            "what_worked": (
                f"Measured {cuts_detected} cut(s) across {duration:.1f}s ({aspect_ratio}); safe-zone status: {safe_zones_status}."
                if stream_analyzed and duration is not None
                else "Pacing telemetry awaits direct video file decoding."
            ),
            "what_underperformed": (
                f"Found {len(static_segs)} static low-motion window(s) >= 2s and {len(hazard_events)} safe-zone hazard timestamp(s)."
                if stream_analyzed and (static_segs or hazard_events)
                else (
                    "Continuous shot without scene transitions."
                    if stream_analyzed and (cuts_detected == 0)
                    else "Frame-level visual pacing and safe zones could not be measured (stream unavailable or simulated)."
                )
            ),
            "why_it_happened": (
                f"Edge/text overlap inside bottom 22% / right 18% margins risks obstruction by Instagram captions and action icons."
                if hazard_events
                else "Maintaining visual transitions every 2-4s and keeping overlays inside safe zones avoids feed fatigue."
            ),
            "supporting_evidence": (
                f"Sampled {sampled_frames} frame(s); cuts={cuts_detected}, hazard_ratio={safe_intel.get('hazard_ratio')}, static_ratio={pacing_intel.get('static_visual_ratio')}."
                if stream_analyzed
                else f"Video source={meta.get('video_source')}."
            ),
            "what_to_change": (
                "Move any lower/right graphic overlays into Y=25%-70% safe bounds"
                if hazard_events
                else "Keep overlays centered safely and introduce framing/angle shifts across longer segments."
            ),
            "how_to_implement": (
                f"Adjust overlay position at timestamp(s) {', '.join(str(e['timestamp_sec']) + 's' for e in hazard_events[:4])}."
                if hazard_events
                else "Upload final export in Mode B before publishing to re-verify bottom 22% / right 18% pixels."
            ),
            "follow_up_test_metric": f"Track engagement rate (currently {er_metric.get('formatted', 'N/A')}) after pacing/framing edits.",
            "confidence": pacing_detail["confidence"],
            "limitations": pacing_detail["limitations"],
        },
        {
            "priority": 3,
            "area": "CTA & High-Intent Engagement",
            "what_worked": (
                f"Detected {cta_intel.get('cta_type')} in caption ({', '.join(cta_intel.get('matched_keywords') or [])})."
                if cta_intel.get("has_explicit_cta")
                else "Metrics pipeline tracks available comment, share, and save attribution without fabricating missing figures."
            ),
            "what_underperformed": (
                f"Save rate ({save_rate_fmt}), share rate ({share_rate_fmt}), or explicit caption CTA is weak or unavailable."
            ),
            "why_it_happened": (
                "Without a concrete action prompt tied to the Reel subject, viewers watch passively without saving or commenting."
            ),
            "supporting_evidence": (
                f"Comment rate: {comment_rate_fmt}; Save rate: {save_rate_fmt}; Share rate: {share_rate_fmt}; CTA source: {cta_intel.get('evaluated_from')}."
            ),
            "what_to_change": (
                f"End '{topic_label}' with one explicit action prompt (bookmark/comment/share) tailored directly to this Reel."
            ),
            "how_to_implement": (
                f"Add a closing caption + on-screen prompt inviting viewers to comment a keyword or save '{topic_label}' for later."
            ),
            "follow_up_test_metric": f"Compare comment rate ({comment_rate_fmt}), save rate ({save_rate_fmt}), and share rate ({share_rate_fmt}).",
            "confidence": growth_detail["confidence"],
            "limitations": growth_detail["limitations"],
        },
    ]

    # --------------------------------------------------------------------------
    # 7. Reel-Specific Creative Alternatives Studio
    # --------------------------------------------------------------------------
    subject = topic["topic_phrase"] or topic["opening_line"][:45] or "your Reel topic"
    kw_upper = (topic["keywords"][0].upper() if topic["keywords"] else "GUIDE")
    if len(kw_upper) > 12:
        kw_upper = "GUIDE"
    hashtag_suggestion = topic["hashtag_line"] or "#instagramreels #contentcreator"
    dur_hint = f"{duration:.0f}s" if duration_measured and duration is not None else "short-form"

    lighting_note = (
        f"Current frame brightness is {avg_brightness} ({lighting_quality.lower()}); boost key-light exposure before exporting."
        if avg_brightness is not None and lighting_quality == "UNDEREXPOSED"
        else (
            f"Current frame brightness is {avg_brightness} ({lighting_quality.lower()}); pull back highlights cleanly."
            if avg_brightness is not None and lighting_quality == "OVEREXPOSED"
            else (
                f"Decoded opening frame ({resolution_str}, contrast {avg_contrast}) can serve as a clean cover base."
                if stream_analyzed
                else "Use the sharpest focal frame from the opening 0-2s inside the vertical 4:5 profile grid crop."
            )
        )
    )

    creative_alternatives = {
        "alternative_hooks": [
            {
                "framework": "Direct Subject Hook",
                "hook_text": (
                    f"Here is what most people miss about {subject}."
                    if not topic["opening_line"]
                    else f"Rework your opening line ('{topic['opening_line'][:55]}'): start directly with the core claim on {subject}."
                ),
                "reasoning": f"Targets viewers specifically interested in '{subject}' within the first 2 seconds.",
            },
            {
                "framework": "Outcome / Curiosity Gap",
                "hook_text": f"What actually changed when I tested {subject} ({dur_hint} breakdown).",
                "reasoning": "Pairs specific subject matter with concrete expectation setting for higher 3-second hold.",
            },
            {
                "framework": "Mistake Prevention",
                "hook_text": f"Before you try {subject}, check these details in the first 3 seconds.",
                "reasoning": "Addresses friction or common errors tied directly to this Reel's subject.",
            },
            {
                "framework": "Actionable Checklist",
                "hook_text": f"Save this {dur_hint} breakdown on {subject} so you can reference it later.",
                "reasoning": "Sets clear bookmark/reference utility tied to the actual content topic.",
            },
        ],
        "thumbnail_concepts": [
            {
                "visual_direction": lighting_note,
                "overlay_text": f"{subject.upper()[:28]}",
                "focal_point": (
                    f"Keep title safely between Y=30%-60% ({safe_zones_status} checked on {sampled_frames} frame(s))."
                    if stream_analyzed
                    else "Center overlay text inside vertical 4:5 grid bounds away from bottom 22%."
                ),
            },
            {
                "visual_direction": (
                    f"Use high-contrast crop from {'timestamp ' + str(cut_times[0]) + 's' if cut_times else 'opening action frame'} with clean subject separation."
                ),
                "overlay_text": f"HOW TO: {subject.upper()[:22]}",
                "focal_point": "High-contrast 3-5 word label legible at profile grid size.",
            },
            {
                "visual_direction": f"Visual state framing emphasizing key takeaway for '{subject}'.",
                "overlay_text": f"SAVE FOR {kw_upper}",
                "focal_point": "Subject eye-line / primary action clear of right 18% icon rail.",
            },
        ],
        "caption_suggestions": [
            {
                "variation_name": f"Topic-Focused Breakdown ({subject[:28]})",
                "text": (
                    f"{topic['opening_line'] or f'Quick breakdown on {subject}.'}\n\n"
                    f"Key focus for this {dur_hint} Reel:\n"
                    f"- Why {subject} matters right now\n"
                    f"- Exact detail to look for at the key moment\n\n"
                    f"Save this post or comment {kw_upper} if you want a deeper breakdown."
                ),
                "suggested_hashtags": hashtag_suggestion,
            },
            {
                "variation_name": "Concise Save & Share Prompt",
                "text": (
                    f"{subject.capitalize()} in {dur_hint}.\n\n"
                    "Bookmark this for your next session and share it with someone working on the same thing."
                ),
                "suggested_hashtags": hashtag_suggestion,
            },
        ],
        "cta_variations": [
            {
                "type": "Topic Keyword Comment Prompt",
                "cta_text": f"Comment '{kw_upper}' if you want more examples covering {subject}.",
            },
            {
                "type": "Bookmark / Save Prompt",
                "cta_text": f"Save this {subject} breakdown so you can revisit it when you need it.",
            },
            {
                "type": "Targeted Share Prompt",
                "cta_text": f"Send this Reel to someone currently working on {subject}.",
            },
        ],
        "revised_script": {
            "hook": (
                f"[00:00-00:03] Open directly on '{topic['opening_line'][:65] or subject}' with crisp lighting and an immediate visual shift."
            ),
            "body": (
                f"[00:03-{_fmt_sec(max(4.0, (duration or 20.0) * 0.7))}] Deliver the core walkthrough on {subject}"
                + (
                    f" aligned around visual cuts ({cuts_detected if cuts_detected is not None else 0} observed)."
                    if stream_analyzed
                    else " with clear visual transitions every 2-4s."
                )
            ),
            "payoff": (
                f"[{_fmt_sec(max(4.0, (duration or 20.0) * 0.7))}-{_fmt_sec(max(5.0, (duration or 24.0) * 0.88))}] Show the concrete result/takeaway for {subject} clearly inside the safe zone."
            ),
            "cta": (
                f"[{_fmt_sec(max(5.0, (duration or 24.0) * 0.88))}-{_fmt_sec(duration or 26.0)}] Close with: 'Save this or comment {kw_upper} for {subject}.'"
            ),
            "shot_notes": (
                f"Based on actual stream: {resolution_str or 'aspect unknown'}, {fps_val or 'FPS unknown'} fps, "
                f"{cuts_detected if cuts_detected is not None else 'unmeasured'} cut(s), safe_zones={safe_zones_status}."
            ),
        },
    }

    # --------------------------------------------------------------------------
    # 8. Transparent Provenance & Metric Source Audit Breakdown
    # --------------------------------------------------------------------------
    measured_list: List[str] = []
    calculated_list: List[str] = []
    simulated_list: List[str] = []
    unavailable_list: List[str] = []
    for k, m in performance_metrics.items():
        if not isinstance(m, dict):
            continue
        cat = m.get("category", "UNAVAILABLE")
        if cat == "MEASURED":
            measured_list.append(k)
        elif cat == "CALCULATED":
            calculated_list.append(k)
        elif cat == "SIMULATED":
            simulated_list.append(k)
        else:
            unavailable_list.append(k)

    if stream_analyzed:
        measured_list.extend(["video_duration", "video_fps", "video_resolution", "visual_cuts"])

    metric_source_mode = (
        "SANDBOX_SIMULATION"
        if is_simulated_metrics
        else (
            "META_GRAPH_API"
            if is_connected
            else ("USER_DECLARED" if measured_list and any(performance_metrics.get(k, {}).get("source") == "User Self-Reported Input" for k in performance_metrics) else "UNAVAILABLE")
        )
    )

    provenance_limitations: List[str] = []
    if is_simulated:
        provenance_limitations.append("SANDBOX SIMULATION: Demo figures shown for testing — NOT live Instagram insights.")
    if not stream_analyzed:
        video_lim = meta.get("limitation")
        if video_lim:
            provenance_limitations.append(video_lim)
        else:
            provenance_limitations.append("Video frames/pixels were not decoded locally; duration, FPS, resolution, and visual cuts could not be measured.")
    if not audio_available:
        provenance_limitations.append("Spoken audio track was not transcribed; WPM and audio dead-air pauses were not measured.")
    if not timestamped_retention_available:
        provenance_limitations.append("Per-second retention / watch-time drop-off curve is unavailable and was NOT claimed as measured.")

    provenance = {
        "engine": "Woka Multimodal Reel Intelligence v2.1 (Grounded Audit)",
        "analysis_mode": analysis_mode,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "is_simulated": is_simulated,
        "metric_source_mode": metric_source_mode,
        "video_source": meta.get("video_source", "UNAVAILABLE"),
        "video_stream_analyzed": stream_analyzed,
        "video_limitation": meta.get("limitation"),
        "duration_measured": duration_measured,
        "fps_measured": bool(meta.get("fps_measured")),
        "video_fps": fps_val,
        "video_duration_seconds": duration,
        "audio_speech_analyzed": audio_available,
        "caption_analyzed": bool(topic["has_text"]),
        "is_retention_measured": bool(timestamped_retention_available and not is_simulated),
        "metric_breakdown": {
            "measured": measured_list,
            "calculated": calculated_list,
            "simulated": simulated_list,
            "estimated": [
                k for k, sd in scores.items()
                if isinstance(sd, dict) and sd.get("score_type") == "AI_ESTIMATE" and sd.get("data_available")
            ],
            "unavailable": unavailable_list,
        },
        "limitations": provenance_limitations,
    }

    return {
        "scores": scores,
        "timeline_findings": timeline_findings,
        "prioritized_action_plan": action_plan,
        "creative_alternatives": creative_alternatives,
        "provenance": provenance,
    }
