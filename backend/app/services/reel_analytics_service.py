from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

# Industry benchmarks for Instagram Reels (standard creator baseline)
BENCHMARKS = {
    "like_rate_views": {"avg": 0.045, "good": 0.075, "excellent": 0.12},     # 4.5% - 7.5%
    "comment_rate": {"avg": 0.003, "good": 0.008, "excellent": 0.015},      # 0.3% - 0.8%
    "share_rate": {"avg": 0.012, "good": 0.025, "excellent": 0.050},        # 1.2% - 2.5% (viral catalyst)
    "save_rate": {"avg": 0.015, "good": 0.035, "excellent": 0.070},         # 1.5% - 3.5% (high intent)
    "engagement_rate": {"avg": 0.050, "good": 0.085, "excellent": 0.140},   # 5.0% - 8.5%
    "watch_ratio": {"avg": 0.55, "good": 0.70, "excellent": 0.85},          # 55% - 70%
    "follow_conversion": {"avg": 0.002, "good": 0.005, "excellent": 0.010}  # 0.2% - 0.5%
}

def classify_benchmark_status(metric_key: str, val: Optional[float]) -> str:
    if val is None:
        return "N/A"
    bm = BENCHMARKS.get(metric_key)
    if not bm:
        return "AVERAGE"
    if val >= bm["good"]:
        return "ABOVE_AVERAGE"
    elif val >= bm["avg"]:
        return "AVERAGE"
    else:
        return "BELOW_AVERAGE"


def calculate_reel_performance_metrics(
    views: int,
    likes: int,
    comments: int,
    shares: int = 0,
    saves: int = 0,
    reach: Optional[int] = None,
    impressions: Optional[int] = None,
    avg_watch_time: Optional[float] = None,
    total_watch_time: Optional[float] = None,
    follows_attributed: Optional[int] = None,
    video_duration_seconds: float = 30.0,
    historical_avg_views: Optional[int] = None,
    source_type: str = "PUBLIC_SCRAPE_FALLBACK"
) -> Dict[str, Any]:
    """
    Computes rigorous, mathematically transparent performance metrics for an Instagram Reel.
    Every metric specifies numerator, denominator, benchmark comparison, and explicit limitations.
    """
    metrics = {}
    is_connected = (source_type == "META_GRAPH_API" or source_type == "SANDBOX_SIMULATED")
    safe_views = max(1, views) if views > 0 else 0

    # 1. Raw Counts
    metrics["views"] = {
        "name": "Total Views / Plays",
        "value": float(views),
        "formatted": f"{views:,}",
        "numerator": "Total recorded Reel plays",
        "denominator": "None (absolute integer)",
        "time_window": "Lifetime",
        "source": "Meta Graph API (video_views)" if is_connected else "Public Reel Scraper / User Input",
        "benchmark": f"{historical_avg_views:,} avg" if historical_avg_views else "N/A",
        "benchmark_status": "N/A" if not historical_avg_views else ("ABOVE_AVERAGE" if views >= historical_avg_views else "BELOW_AVERAGE"),
        "limitations": "In Public Mode, view counts may be delayed by Instagram CDN caching."
    }

    metrics["reach"] = {
        "name": "Unique Reach",
        "value": float(reach) if reach is not None else None,
        "formatted": f"{reach:,}" if reach is not None else "N/A (Connected Account Only)",
        "numerator": "Count of unique accounts who viewed the Reel at least once",
        "denominator": "None (unique accounts)",
        "time_window": "Lifetime",
        "source": "Meta Graph API (reach)" if is_connected else "Unavailable in Public Mode",
        "benchmark": "70% - 90% of views typical",
        "benchmark_status": "N/A" if reach is None else ("ABOVE_AVERAGE" if (views > 0 and reach / views >= 0.8) else "AVERAGE"),
        "limitations": "Official Meta Graph API permission `pages_read_engagement` / Professional account required."
    }

    metrics["likes"] = {
        "name": "Likes",
        "value": float(likes),
        "formatted": f"{likes:,}",
        "numerator": "Total like reactions",
        "denominator": "None (absolute integer)",
        "time_window": "Lifetime",
        "source": "Meta Graph API / Public Scrape",
        "benchmark": "N/A",
        "benchmark_status": "N/A",
        "limitations": "Visible publicly unless creator explicitly chose to hide like counts on Instagram."
    }

    metrics["comments"] = {
        "name": "Comments",
        "value": float(comments),
        "formatted": f"{comments:,}",
        "numerator": "Total top-level comments and replies",
        "denominator": "None (absolute integer)",
        "time_window": "Lifetime",
        "source": "Meta Graph API / Public Scrape",
        "benchmark": "N/A",
        "benchmark_status": "N/A",
        "limitations": "Includes creator's own responses to fan comments."
    }

    metrics["shares"] = {
        "name": "Shares",
        "value": float(shares),
        "formatted": f"{shares:,}" if (is_connected or shares > 0) else "N/A (Requires Connected Insights)",
        "numerator": "DM shares and external share clicks",
        "denominator": "None (absolute integer)",
        "time_window": "Lifetime",
        "source": "Meta Graph API (shares)" if is_connected else "User Declared / Estimated",
        "benchmark": "N/A",
        "benchmark_status": "N/A",
        "limitations": "Private direct message shares cannot be scraped from public web without Meta authentication."
    }

    metrics["saves"] = {
        "name": "Saves / Bookmarks",
        "value": float(saves),
        "formatted": f"{saves:,}" if (is_connected or saves > 0) else "N/A (Requires Connected Insights)",
        "numerator": "Bookmarks saved into user collections",
        "denominator": "None (absolute integer)",
        "time_window": "Lifetime",
        "source": "Meta Graph API (saved)" if is_connected else "User Declared / Estimated",
        "benchmark": "N/A",
        "benchmark_status": "N/A",
        "limitations": "Save counts are private to the account holder."
    }

    # 2. Calculated Rates
    like_rate_views = round(likes / safe_views, 4) if safe_views > 0 else 0.0
    metrics["like_rate_views"] = {
        "name": "Like Rate (Views)",
        "value": like_rate_views,
        "formatted": f"{round(like_rate_views * 100, 2)}%",
        "numerator": f"Likes ({likes:,})",
        "denominator": f"Total Views ({views:,})",
        "time_window": "Lifetime",
        "source": "Calculated Ratio",
        "benchmark": "4.5% - 7.5% typical",
        "benchmark_status": classify_benchmark_status("like_rate_views", like_rate_views),
        "limitations": "Does not differentiate between repeat views by the same viewer."
    }

    if reach and reach > 0:
        like_rate_reach = round(likes / reach, 4)
        metrics["like_rate_reach"] = {
            "name": "Like Rate (Unique Reach)",
            "value": like_rate_reach,
            "formatted": f"{round(like_rate_reach * 100, 2)}%",
            "numerator": f"Likes ({likes:,})",
            "denominator": f"Unique Reach ({reach:,})",
            "time_window": "Lifetime",
            "source": "Calculated Ratio (Connected Insights)",
            "benchmark": "5.5% - 9.0% typical",
            "benchmark_status": "ABOVE_AVERAGE" if like_rate_reach >= 0.075 else "AVERAGE",
            "limitations": "Calculated strictly against unique persons reached."
        }
    else:
        metrics["like_rate_reach"] = {
            "name": "Like Rate (Unique Reach)",
            "value": None,
            "formatted": "N/A",
            "numerator": "Likes",
            "denominator": "Reach (Unavailable in Public Mode)",
            "time_window": "Lifetime",
            "source": "N/A",
            "benchmark": "5.5% - 9.0%",
            "benchmark_status": "N/A",
            "limitations": "Reach is a private Meta Graph API metric."
        }

    comment_rate = round(comments / safe_views, 4) if safe_views > 0 else 0.0
    metrics["comment_rate"] = {
        "name": "Comment Rate",
        "value": comment_rate,
        "formatted": f"{round(comment_rate * 100, 2)}%",
        "numerator": f"Comments ({comments:,})",
        "denominator": f"Total Views ({views:,})",
        "time_window": "Lifetime",
        "source": "Calculated Ratio",
        "benchmark": "0.3% - 0.8% typical",
        "benchmark_status": classify_benchmark_status("comment_rate", comment_rate),
        "limitations": "Comment automations and creator replies can inflate this ratio."
    }

    share_rate = round(shares / safe_views, 4) if safe_views > 0 and (is_connected or shares > 0) else None
    metrics["share_rate"] = {
        "name": "Share Rate",
        "value": share_rate,
        "formatted": f"{round(share_rate * 100, 2)}%" if share_rate is not None else "N/A (Connected Only)",
        "numerator": f"Shares ({shares:,})",
        "denominator": f"Total Views ({views:,})",
        "time_window": "Lifetime",
        "source": "Calculated Ratio",
        "benchmark": "1.2% - 2.5% typical",
        "benchmark_status": classify_benchmark_status("share_rate", share_rate),
        "limitations": "Strongest indicator of algorithmic recommendation."
    }

    save_rate = round(saves / safe_views, 4) if safe_views > 0 and (is_connected or saves > 0) else None
    metrics["save_rate"] = {
        "name": "Save Rate",
        "value": save_rate,
        "formatted": f"{round(save_rate * 100, 2)}%" if save_rate is not None else "N/A (Connected Only)",
        "numerator": f"Saves ({saves:,})",
        "denominator": f"Total Views ({views:,})",
        "time_window": "Lifetime",
        "source": "Calculated Ratio",
        "benchmark": "1.5% - 3.5% typical",
        "benchmark_status": classify_benchmark_status("save_rate", save_rate),
        "limitations": "Primary proxy for high evergreen utility and educational value."
    }

    # Engagement Rate
    # Formula: (Likes + Comments + Shares + Saves) / Reach (or Views if Reach unavailable)
    total_engagements = likes + comments + (shares or 0) + (saves or 0)
    if reach and reach > 0:
        er = round(total_engagements / reach, 4)
        er_denom = f"Unique Reach ({reach:,})"
        er_label = "Engagement Rate (Reach)"
    else:
        er = round(total_engagements / safe_views, 4) if safe_views > 0 else 0.0
        er_denom = f"Total Views ({views:,})"
        er_label = "Engagement Rate (Views)"

    metrics["engagement_rate"] = {
        "name": er_label,
        "value": er,
        "formatted": f"{round(er * 100, 2)}%",
        "numerator": f"Total Engagements ({total_engagements:,})",
        "denominator": er_denom,
        "time_window": "Lifetime",
        "source": "Calculated Aggregate",
        "benchmark": "5.0% - 8.5% typical",
        "benchmark_status": classify_benchmark_status("engagement_rate", er),
        "limitations": "Aggregates likes, comments, shares, and saves. Labeled by denominator."
    }

    # Watch ratio
    if avg_watch_time and video_duration_seconds > 0:
        watch_ratio = round(avg_watch_time / video_duration_seconds, 3)
        metrics["watch_ratio"] = {
            "name": "Average Watch Ratio",
            "value": watch_ratio,
            "formatted": f"{round(watch_ratio * 100, 1)}%",
            "numerator": f"Average Watch Time ({avg_watch_time:.1f}s)",
            "denominator": f"Video Duration ({video_duration_seconds:.1f}s)",
            "time_window": "Lifetime",
            "source": "Meta Graph API (avg_watch_time)",
            "benchmark": "55% - 70% typical",
            "benchmark_status": classify_benchmark_status("watch_ratio", watch_ratio),
            "limitations": "Requires Meta Graph API video_insights permission."
        }
    else:
        metrics["watch_ratio"] = {
            "name": "Average Watch Ratio",
            "value": None,
            "formatted": "N/A (Connected Account Only)",
            "numerator": "Average Watch Time",
            "denominator": f"Video Duration ({video_duration_seconds:.1f}s)",
            "time_window": "Lifetime",
            "source": "Meta Graph API (avg_watch_time)",
            "benchmark": "55% - 70%",
            "benchmark_status": "N/A",
            "limitations": "Private retention metric not accessible in Public URL mode."
        }

    # Baseline comparison
    if historical_avg_views and historical_avg_views > 0:
        delta = round(((views - historical_avg_views) / historical_avg_views) * 100, 1)
        metrics["benchmark_delta"] = {
            "name": "Views vs Account Baseline",
            "value": delta,
            "formatted": f"{'+' if delta >= 0 else ''}{delta}%",
            "numerator": f"Reel Views ({views:,}) - Baseline ({historical_avg_views:,})",
            "denominator": f"Baseline ({historical_avg_views:,})",
            "time_window": "30-Day Historical Account Average",
            "source": "Woka Historical Analytics Index",
            "benchmark": "0% (Baseline Match)",
            "benchmark_status": "ABOVE_AVERAGE" if delta >= 15.0 else ("BELOW_AVERAGE" if delta <= -15.0 else "AVERAGE"),
            "limitations": "Calculated against the creator's last 30 days of published Reels."
        }
    else:
        metrics["benchmark_delta"] = {
            "name": "Views vs Account Baseline",
            "value": None,
            "formatted": "N/A (Requires Historical Baseline)",
            "numerator": "Reel Views",
            "denominator": "Account Historical Average",
            "time_window": "30-Day Account Average",
            "source": "Woka Creator Profile",
            "benchmark": "0%",
            "benchmark_status": "N/A",
            "limitations": "Requires at least 3 previous Reels analyzed in Woka to establish an empirical baseline."
        }

    # Follow conversion
    if follows_attributed is not None and reach and reach > 0:
        f_conv = round(follows_attributed / reach, 5)
        metrics["follow_conversion"] = {
            "name": "Follower Conversion Rate",
            "value": f_conv,
            "formatted": f"{round(f_conv * 100, 3)}%",
            "numerator": f"Attributed Follows ({follows_attributed})",
            "denominator": f"Unique Reach ({reach:,})",
            "time_window": "Lifetime",
            "source": "Meta Graph API (follows_attributed)",
            "benchmark": "0.2% - 0.5% typical",
            "benchmark_status": classify_benchmark_status("follow_conversion", f_conv),
            "limitations": "Only measurable when Meta Graph API returns attributable follower events."
        }
    else:
        metrics["follow_conversion"] = {
            "name": "Follower Conversion Rate",
            "value": None,
            "formatted": "N/A",
            "numerator": "Attributed Follows",
            "denominator": "Unique Reach",
            "time_window": "Lifetime",
            "source": "Meta Graph API",
            "benchmark": "0.2% - 0.5%",
            "benchmark_status": "N/A",
            "limitations": "Requires connected professional account and supported attribution data."
        }

    return metrics
