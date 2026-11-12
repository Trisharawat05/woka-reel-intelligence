from typing import Dict, Any, Optional

# Industry benchmarks for Instagram Reels (standard creator baseline)
BENCHMARKS = {
    "like_rate_views": {"avg": 0.045, "good": 0.075, "excellent": 0.12},     # 4.5% - 7.5%
    "comment_rate": {"avg": 0.003, "good": 0.008, "excellent": 0.015},      # 0.3% - 0.8%
    "share_rate": {"avg": 0.012, "good": 0.025, "excellent": 0.050},        # 1.2% - 2.5%
    "save_rate": {"avg": 0.015, "good": 0.035, "excellent": 0.070},         # 1.5% - 3.5%
    "engagement_rate": {"avg": 0.050, "good": 0.085, "excellent": 0.140},   # 5.0% - 8.5%
    "watch_ratio": {"avg": 0.55, "good": 0.70, "excellent": 0.85},          # 55% - 70%
    "follow_conversion": {"avg": 0.002, "good": 0.005, "excellent": 0.010}, # 0.2% - 0.5%
}


def classify_benchmark_status(metric_key: str, val: Optional[float]) -> str:
    if val is None:
        return "N/A"
    bm = BENCHMARKS.get(metric_key)
    if not bm:
        return "AVERAGE"
    if val >= bm["good"]:
        return "ABOVE_AVERAGE"
    if val >= bm["avg"]:
        return "AVERAGE"
    return "BELOW_AVERAGE"


def _build_unavailable_metric(
    name: str,
    formatted: str,
    numerator: str,
    denominator: str,
    time_window: str,
    benchmark: Optional[str],
    limitations: str,
    is_simulated: bool = False,
) -> Dict[str, Any]:
    return {
        "name": name,
        "value": None,
        "formatted": formatted,
        "numerator": numerator,
        "denominator": denominator,
        "time_window": time_window,
        "source": "Unavailable (Not Returned / Applicable)",
        "category": "UNAVAILABLE",
        "is_simulated": is_simulated,
        "benchmark": benchmark,
        "benchmark_status": "N/A",
        "limitations": limitations,
    }


def calculate_reel_performance_metrics(
    views: Optional[int] = None,
    likes: Optional[int] = None,
    comments: Optional[int] = None,
    shares: Optional[int] = None,
    saves: Optional[int] = None,
    reach: Optional[int] = None,
    impressions: Optional[int] = None,
    avg_watch_time: Optional[float] = None,
    total_watch_time: Optional[float] = None,
    follows_attributed: Optional[int] = None,
    video_duration_seconds: Optional[float] = None,
    historical_avg_views: Optional[int] = None,
    source_type: str = "PUBLIC_SCRAPE_FALLBACK",
    total_interactions: Optional[int] = None,
    timestamped_retention_available: bool = False,
) -> Dict[str, Any]:
    """
    Computes strictly grounded performance metrics for an Instagram Reel.
    Explicitly separates MEASURED, CALCULATED, SIMULATED, and UNAVAILABLE metrics
    and never invents values for missing inputs.
    """
    metrics: Dict[str, Any] = {}
    is_simulated = source_type in ("SANDBOX_SIMULATION", "SANDBOX_SIMULATED")
    is_live_meta = source_type == "META_GRAPH_API"
    is_user_declared = source_type == "USER_DECLARED"
    raw_category = "SIMULATED" if is_simulated else "MEASURED"
    calc_category = "SIMULATED" if is_simulated else "CALCULATED"

    def _raw_source(meta_field: str, public_label: str) -> str:
        if is_simulated:
            return f"Sandbox Simulation (Demo Data: {meta_field} — Not Live Meta Graph API)"
        if is_live_meta:
            return f"Meta Graph API ({meta_field})"
        if is_user_declared:
            return "User Self-Reported Input"
        return public_label

    sim_limitation_suffix = (
        " Simulated demo metric for sandbox preview; not live Instagram account performance."
        if is_simulated
        else ""
    )

    # 1. Views / Plays
    if views is not None:
        bm_status = "N/A"
        if historical_avg_views and historical_avg_views > 0:
            bm_status = "ABOVE_AVERAGE" if views >= historical_avg_views else "BELOW_AVERAGE"
        metrics["views"] = {
            "name": "Total Views / Plays",
            "value": float(views),
            "formatted": f"{views:,}",
            "numerator": "Total recorded Reel plays",
            "denominator": "None (absolute integer)",
            "time_window": "Lifetime",
            "source": _raw_source("views", "Public Reel Input"),
            "category": raw_category,
            "is_simulated": is_simulated,
            "benchmark": f"{historical_avg_views:,} avg" if historical_avg_views else "N/A",
            "benchmark_status": bm_status,
            "limitations": (
                "Self-reported by creator rather than verified via Meta Insights."
                if is_user_declared
                else (
                    "Returned by Meta Graph API Insights endpoint."
                    if is_live_meta
                    else ("Zero plays supplied/recorded." if not is_simulated else sim_limitation_suffix.strip())
                )
            ),
        }
    else:
        metrics["views"] = _build_unavailable_metric(
            name="Total Views / Plays",
            formatted="N/A (Unavailable)",
            numerator="Total recorded Reel plays",
            denominator="None (absolute integer)",
            time_window="Lifetime",
            benchmark=f"{historical_avg_views:,} avg" if historical_avg_views else "N/A",
            limitations=(
                "Play count unavailable: no Meta Insights `views` metric or user-declared views supplied."
            ),
            is_simulated=is_simulated,
        )

    # 2. Unique Reach
    if reach is not None:
        reach_ratio_status = "N/A"
        if views is not None and views > 0:
            reach_ratio_status = "ABOVE_AVERAGE" if (reach / views >= 0.8) else "AVERAGE"
        metrics["reach"] = {
            "name": "Unique Reach",
            "value": float(reach),
            "formatted": f"{reach:,}",
            "numerator": "Count of unique accounts who viewed the Reel at least once",
            "denominator": "None (unique accounts)",
            "time_window": "Lifetime",
            "source": _raw_source("reach", "Unavailable"),
            "category": raw_category,
            "is_simulated": is_simulated,
            "benchmark": "70% - 90% of views typical",
            "benchmark_status": reach_ratio_status,
            "limitations": (
                sim_limitation_suffix.strip()
                if is_simulated
                else "Reported directly from Meta Graph API (`reach`)."
            ),
        }
    else:
        metrics["reach"] = _build_unavailable_metric(
            name="Unique Reach",
            formatted="N/A (Connected Account Only)",
            numerator="Count of unique accounts who viewed the Reel at least once",
            denominator="None (unique accounts)",
            time_window="Lifetime",
            benchmark="70% - 90% of views typical",
            limitations="Unique reach requires an authenticated Meta Graph API connection returning `reach`.",
            is_simulated=is_simulated,
        )

    # 3. Likes
    if likes is not None:
        metrics["likes"] = {
            "name": "Likes",
            "value": float(likes),
            "formatted": f"{likes:,}",
            "numerator": "Total like reactions",
            "denominator": "None (absolute integer)",
            "time_window": "Lifetime",
            "source": _raw_source("like_count", "Public Reel Input"),
            "category": raw_category,
            "is_simulated": is_simulated,
            "benchmark": "N/A",
            "benchmark_status": "N/A",
            "limitations": (
                sim_limitation_suffix.strip()
                if is_simulated
                else (
                    "Self-reported like count."
                    if is_user_declared
                    else "Visible unless creator hides public like counts or Meta omits `like_count`."
                )
            ),
        }
    else:
        metrics["likes"] = _build_unavailable_metric(
            name="Likes",
            formatted="N/A (Unavailable)",
            numerator="Total like reactions",
            denominator="None (absolute integer)",
            time_window="Lifetime",
            benchmark="N/A",
            limitations="Like count was not provided or was omitted from the Meta Media response.",
            is_simulated=is_simulated,
        )

    # 4. Comments
    if comments is not None:
        metrics["comments"] = {
            "name": "Comments",
            "value": float(comments),
            "formatted": f"{comments:,}",
            "numerator": "Total top-level comments and replies",
            "denominator": "None (absolute integer)",
            "time_window": "Lifetime",
            "source": _raw_source("comments_count", "Public Reel Input"),
            "category": raw_category,
            "is_simulated": is_simulated,
            "benchmark": "N/A",
            "benchmark_status": "N/A",
            "limitations": (
                sim_limitation_suffix.strip()
                if is_simulated
                else "Includes creator replies when present."
            ),
        }
    else:
        metrics["comments"] = _build_unavailable_metric(
            name="Comments",
            formatted="N/A (Unavailable)",
            numerator="Total top-level comments and replies",
            denominator="None (absolute integer)",
            time_window="Lifetime",
            benchmark="N/A",
            limitations="Comment count was not provided or was omitted from the Meta Media response.",
            is_simulated=is_simulated,
        )

    # 5. Shares
    if shares is not None and (is_live_meta or is_simulated or is_user_declared or shares > 0):
        metrics["shares"] = {
            "name": "Shares",
            "value": float(shares),
            "formatted": f"{shares:,}",
            "numerator": "DM shares and external share clicks",
            "denominator": "None (absolute integer)",
            "time_window": "Lifetime",
            "source": _raw_source("shares", "User Self-Reported Input"),
            "category": raw_category,
            "is_simulated": is_simulated,
            "benchmark": "N/A",
            "benchmark_status": "N/A",
            "limitations": (
                sim_limitation_suffix.strip()
                if is_simulated
                else "Private DM shares are returned only via authenticated Meta Insights or explicit creator input."
            ),
        }
    else:
        metrics["shares"] = _build_unavailable_metric(
            name="Shares",
            formatted="N/A (Requires Connected Insights)",
            numerator="DM shares and external share clicks",
            denominator="None (absolute integer)",
            time_window="Lifetime",
            benchmark="N/A",
            limitations="Share counts are private and unavailable without Meta Insights or user input.",
            is_simulated=is_simulated,
        )

    # 6. Saves
    if saves is not None and (is_live_meta or is_simulated or is_user_declared or saves > 0):
        metrics["saves"] = {
            "name": "Saves / Bookmarks",
            "value": float(saves),
            "formatted": f"{saves:,}",
            "numerator": "Bookmarks saved into user collections",
            "denominator": "None (absolute integer)",
            "time_window": "Lifetime",
            "source": _raw_source("saved", "User Self-Reported Input"),
            "category": raw_category,
            "is_simulated": is_simulated,
            "benchmark": "N/A",
            "benchmark_status": "N/A",
            "limitations": (
                sim_limitation_suffix.strip()
                if is_simulated
                else "Save counts are private to the connected account holder."
            ),
        }
    else:
        metrics["saves"] = _build_unavailable_metric(
            name="Saves / Bookmarks",
            formatted="N/A (Requires Connected Insights)",
            numerator="Bookmarks saved into user collections",
            denominator="None (absolute integer)",
            time_window="Lifetime",
            benchmark="N/A",
            limitations="Save counts are private and unavailable without Meta Insights or user input.",
            is_simulated=is_simulated,
        )

    # 7. Calculated Rates (never invent rates when required inputs are unavailable)
    has_positive_views = views is not None and views > 0
    explicit_zero_views = views == 0

    if likes is not None and (has_positive_views or explicit_zero_views):
        like_rate_views = round(likes / views, 4) if has_positive_views else 0.0
        metrics["like_rate_views"] = {
            "name": "Like Rate (Views)",
            "value": like_rate_views,
            "formatted": f"{round(like_rate_views * 100, 2)}%",
            "numerator": f"Likes ({likes:,})",
            "denominator": f"Total Views ({views:,})",
            "time_window": "Lifetime",
            "source": "Sandbox Simulation (Calculated Ratio)" if is_simulated else "Calculated Ratio (Likes / Views)",
            "category": calc_category,
            "is_simulated": is_simulated,
            "benchmark": "4.5% - 7.5% typical",
            "benchmark_status": classify_benchmark_status("like_rate_views", like_rate_views),
            "limitations": ("Based on sandbox demo counts." if is_simulated else "Does not separate repeat plays from unique viewers."),
        }
    else:
        metrics["like_rate_views"] = _build_unavailable_metric(
            name="Like Rate (Views)",
            formatted="N/A",
            numerator="Likes",
            denominator="Total Views",
            time_window="Lifetime",
            benchmark="4.5% - 7.5% typical",
            limitations="Requires both Likes and Views counts.",
            is_simulated=is_simulated,
        )

    if likes is not None and reach is not None and reach > 0:
        like_rate_reach = round(likes / reach, 4)
        metrics["like_rate_reach"] = {
            "name": "Like Rate (Unique Reach)",
            "value": like_rate_reach,
            "formatted": f"{round(like_rate_reach * 100, 2)}%",
            "numerator": f"Likes ({likes:,})",
            "denominator": f"Unique Reach ({reach:,})",
            "time_window": "Lifetime",
            "source": (
                "Sandbox Simulation (Calculated Ratio)"
                if is_simulated
                else "Calculated Ratio (Connected Insights)"
            ),
            "category": calc_category,
            "is_simulated": is_simulated,
            "benchmark": "5.5% - 9.0% typical",
            "benchmark_status": "ABOVE_AVERAGE" if like_rate_reach >= 0.075 else "AVERAGE",
            "limitations": ("Based on sandbox demo counts." if is_simulated else "Calculated against unique accounts reached."),
        }
    else:
        metrics["like_rate_reach"] = _build_unavailable_metric(
            name="Like Rate (Unique Reach)",
            formatted="N/A",
            numerator="Likes",
            denominator="Reach (Unavailable)",
            time_window="Lifetime",
            benchmark="5.5% - 9.0%",
            limitations="Requires both Unique Reach (`reach`) and Likes (`like_count`).",
            is_simulated=is_simulated,
        )

    if comments is not None and (has_positive_views or explicit_zero_views):
        comment_rate = round(comments / views, 4) if has_positive_views else 0.0
        metrics["comment_rate"] = {
            "name": "Comment Rate",
            "value": comment_rate,
            "formatted": f"{round(comment_rate * 100, 2)}%",
            "numerator": f"Comments ({comments:,})",
            "denominator": f"Total Views ({views:,})",
            "time_window": "Lifetime",
            "source": "Sandbox Simulation (Calculated Ratio)" if is_simulated else "Calculated Ratio (Comments / Views)",
            "category": calc_category,
            "is_simulated": is_simulated,
            "benchmark": "0.3% - 0.8% typical",
            "benchmark_status": classify_benchmark_status("comment_rate", comment_rate),
            "limitations": ("Based on sandbox demo counts." if is_simulated else "Creator replies in the comment thread are included in comments_count."),
        }
    else:
        metrics["comment_rate"] = _build_unavailable_metric(
            name="Comment Rate",
            formatted="N/A",
            numerator="Comments",
            denominator="Total Views",
            time_window="Lifetime",
            benchmark="0.3% - 0.8% typical",
            limitations="Requires both Comments and Views counts.",
            is_simulated=is_simulated,
        )

    if shares is not None and (is_live_meta or is_simulated or is_user_declared or shares > 0) and has_positive_views:
        share_rate = round(shares / views, 4)
        metrics["share_rate"] = {
            "name": "Share Rate",
            "value": share_rate,
            "formatted": f"{round(share_rate * 100, 2)}%",
            "numerator": f"Shares ({shares:,})",
            "denominator": f"Total Views ({views:,})",
            "time_window": "Lifetime",
            "source": "Sandbox Simulation (Calculated Ratio)" if is_simulated else "Calculated Ratio (Shares / Views)",
            "category": calc_category,
            "is_simulated": is_simulated,
            "benchmark": "1.2% - 2.5% typical",
            "benchmark_status": classify_benchmark_status("share_rate", share_rate),
            "limitations": ("Based on sandbox demo counts." if is_simulated else "Measures DM/external shares relative to plays."),
        }
    else:
        metrics["share_rate"] = _build_unavailable_metric(
            name="Share Rate",
            formatted="N/A (Connected Only)",
            numerator="Shares",
            denominator="Total Views",
            time_window="Lifetime",
            benchmark="1.2% - 2.5% typical",
            limitations="Requires both private Shares (`shares`) and Total Views.",
            is_simulated=is_simulated,
        )

    if saves is not None and (is_live_meta or is_simulated or is_user_declared or saves > 0) and has_positive_views:
        save_rate = round(saves / views, 4)
        metrics["save_rate"] = {
            "name": "Save Rate",
            "value": save_rate,
            "formatted": f"{round(save_rate * 100, 2)}%",
            "numerator": f"Saves ({saves:,})",
            "denominator": f"Total Views ({views:,})",
            "time_window": "Lifetime",
            "source": "Sandbox Simulation (Calculated Ratio)" if is_simulated else "Calculated Ratio (Saves / Views)",
            "category": calc_category,
            "is_simulated": is_simulated,
            "benchmark": "1.5% - 3.5% typical",
            "benchmark_status": classify_benchmark_status("save_rate", save_rate),
            "limitations": ("Based on sandbox demo counts." if is_simulated else "Measures bookmarks relative to plays."),
        }
    else:
        metrics["save_rate"] = _build_unavailable_metric(
            name="Save Rate",
            formatted="N/A (Connected Only)",
            numerator="Saves",
            denominator="Total Views",
            time_window="Lifetime",
            benchmark="1.5% - 3.5% typical",
            limitations="Requires both private Saves (`saved`) and Total Views.",
            is_simulated=is_simulated,
        )

    # 8. Engagement Rate
    available_components = []
    component_sum = 0
    missing_components = []
    for label, val in (("Likes", likes), ("Comments", comments), ("Shares", shares), ("Saves", saves)):
        if val is not None:
            available_components.append(label)
            component_sum += val
        else:
            missing_components.append(label)

    # Use Meta total_interactions directly if individual breakdown fields were omitted
    er_numerator_val: Optional[int] = None
    er_numerator_desc = ""
    if available_components and (total_interactions is None or len(available_components) >= 3):
        er_numerator_val = component_sum
        er_numerator_desc = f"Sum of {', '.join(available_components)} ({component_sum:,})"
    elif total_interactions is not None:
        er_numerator_val = total_interactions
        er_numerator_desc = f"Meta Total Interactions ({total_interactions:,})"
        missing_components = [c for c in ("Likes", "Comments", "Shares", "Saves") if c not in available_components]
    elif explicit_zero_views and not available_components:
        er_numerator_val = 0
        er_numerator_desc = "Total Engagements (0)"

    if er_numerator_val is not None and reach is not None and reach > 0:
        er = round(er_numerator_val / reach, 4)
        metrics["engagement_rate"] = {
            "name": "Engagement Rate (Reach)",
            "value": er,
            "formatted": f"{round(er * 100, 2)}%",
            "numerator": er_numerator_desc,
            "denominator": f"Unique Reach ({reach:,})",
            "time_window": "Lifetime",
            "source": "Sandbox Simulation (Calculated Aggregate)" if is_simulated else "Calculated Aggregate",
            "category": calc_category,
            "is_simulated": is_simulated,
            "benchmark": "5.0% - 8.5% typical",
            "benchmark_status": classify_benchmark_status("engagement_rate", er),
            "limitations": (
                ("Based on sandbox demo counts. " if is_simulated else "")
                + (f"Excludes unavailable fields ({', '.join(missing_components)})." if (missing_components and total_interactions is None) else "Aggregates recorded interactions over Unique Reach.")
            ).strip(),
        }
    elif er_numerator_val is not None and (has_positive_views or explicit_zero_views):
        er = round(er_numerator_val / views, 4) if has_positive_views else 0.0
        metrics["engagement_rate"] = {
            "name": "Engagement Rate (Views)",
            "value": er,
            "formatted": f"{round(er * 100, 2)}%",
            "numerator": er_numerator_desc,
            "denominator": f"Total Views ({views:,})",
            "time_window": "Lifetime",
            "source": "Sandbox Simulation (Calculated Aggregate)" if is_simulated else "Calculated Aggregate",
            "category": calc_category,
            "is_simulated": is_simulated,
            "benchmark": "5.0% - 8.5% typical",
            "benchmark_status": classify_benchmark_status("engagement_rate", er),
            "limitations": (
                ("Based on sandbox demo counts. " if is_simulated else "")
                + (f"Private metrics omitted/unavailable ({', '.join(missing_components)})." if missing_components else "Calculated against Total Views (Reach unavailable).")
            ).strip(),
        }
    else:
        metrics["engagement_rate"] = _build_unavailable_metric(
            name="Engagement Rate",
            formatted="N/A (Unavailable)",
            numerator="Interactions",
            denominator="Unique Reach or Views",
            time_window="Lifetime",
            benchmark="5.0% - 8.5% typical",
            limitations="Insufficient engagement or denominator data (Reach/Views unavailable).",
            is_simulated=is_simulated,
        )

    # 9. Watch Ratio (Strictly requires both measured avg_watch_time AND measured duration)
    dur_str = f"{video_duration_seconds:.1f}s" if (video_duration_seconds is not None and video_duration_seconds > 0) else "Unavailable"
    if avg_watch_time is not None and video_duration_seconds is not None and video_duration_seconds > 0:
        watch_ratio = round(avg_watch_time / video_duration_seconds, 3)
        watch_limit = (
            sim_limitation_suffix.strip()
            if is_simulated
            else (
                "Computed from Meta avg_watch_time & video duration; timestamped retention drop-off telemetry was verified."
                if timestamped_retention_available
                else "Computed from summary average watch time (`avg_watch_time`) over duration; per-second retention drop-off curve is NOT available."
            )
        )
        metrics["watch_ratio"] = {
            "name": "Average Watch Ratio",
            "value": watch_ratio,
            "formatted": f"{round(watch_ratio * 100, 1)}%",
            "numerator": f"Average Watch Time ({avg_watch_time:.1f}s)",
            "denominator": f"Video Duration ({dur_str})",
            "time_window": "Lifetime",
            "source": (
                "Sandbox Simulation (Demo Watch Time)"
                if is_simulated
                else "Meta Graph API (avg_watch_time)"
            ),
            "category": "SIMULATED" if is_simulated else "CALCULATED",
            "is_simulated": is_simulated,
            "benchmark": "55% - 70% typical",
            "benchmark_status": classify_benchmark_status("watch_ratio", watch_ratio),
            "limitations": watch_limit,
        }
    else:
        metrics["watch_ratio"] = _build_unavailable_metric(
            name="Average Watch Ratio",
            formatted="N/A (Connected Account Only)",
            numerator="Average Watch Time (Unavailable)",
            denominator=f"Video Duration ({dur_str})",
            time_window="Lifetime",
            benchmark="55% - 70%",
            limitations=(
                "Watch time / retention telemetry is unavailable from Meta Insights or public sources and is not estimated numerically."
            ),
            is_simulated=is_simulated,
        )

    # 10. Baseline Comparison
    if views is not None and historical_avg_views is not None and historical_avg_views > 0:
        delta = round(((views - historical_avg_views) / historical_avg_views) * 100, 1)
        metrics["benchmark_delta"] = {
            "name": "Views vs Account Baseline",
            "value": delta,
            "formatted": f"{'+' if delta >= 0 else ''}{delta}%",
            "numerator": f"Reel Views ({views:,}) - Baseline ({historical_avg_views:,})",
            "denominator": f"Baseline ({historical_avg_views:,})",
            "time_window": "30-Day Historical Account Average",
            "source": "Woka Historical Analytics Index" if not is_simulated else "Sandbox Comparison vs Stored Baseline",
            "category": calc_category,
            "is_simulated": is_simulated,
            "benchmark": "0% (Baseline Match)",
            "benchmark_status": "ABOVE_AVERAGE" if delta >= 15.0 else ("BELOW_AVERAGE" if delta <= -15.0 else "AVERAGE"),
            "limitations": "Calculated against stored 30-day workspace account analytics snapshot.",
        }
    else:
        metrics["benchmark_delta"] = _build_unavailable_metric(
            name="Views vs Account Baseline",
            formatted="N/A (Requires Historical Baseline)",
            numerator="Reel Views",
            denominator="Account Historical Average",
            time_window="30-Day Account Average",
            benchmark="0%",
            limitations="Requires both verified Reel Views and stored 30-day CreatorAnalytics baseline.",
            is_simulated=is_simulated,
        )

    # 11. Follow Conversion
    if follows_attributed is not None and reach is not None and reach > 0:
        f_conv = round(follows_attributed / reach, 5)
        metrics["follow_conversion"] = {
            "name": "Follower Conversion Rate",
            "value": f_conv,
            "formatted": f"{round(f_conv * 100, 3)}%",
            "numerator": f"Attributed Follows ({follows_attributed})",
            "denominator": f"Unique Reach ({reach:,})",
            "time_window": "Lifetime",
            "source": "Sandbox Simulation (Demo Follows)" if is_simulated else "Meta Graph API (follows_attributed)",
            "category": "SIMULATED" if is_simulated else "CALCULATED",
            "is_simulated": is_simulated,
            "benchmark": "0.2% - 0.5% typical",
            "benchmark_status": classify_benchmark_status("follow_conversion", f_conv),
            "limitations": (
                sim_limitation_suffix.strip()
                if is_simulated
                else "Only measurable when Meta Graph API returns attributable follower events."
            ),
        }
    else:
        metrics["follow_conversion"] = _build_unavailable_metric(
            name="Follower Conversion Rate",
            formatted="N/A",
            numerator="Attributed Follows",
            denominator="Unique Reach",
            time_window="Lifetime",
            benchmark="0.2% - 0.5%",
            limitations="Follower attribution per Reel was not returned by Meta Graph API and is unavailable.",
            is_simulated=is_simulated,
        )

    return metrics
