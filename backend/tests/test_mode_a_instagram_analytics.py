import pytest
from unittest.mock import MagicMock, patch

from app.services.video_ingestion.models import PlatformType, RetrievalStatus, VideoMetadata
from app.services.video_ingestion.providers.instagram import (
    InstagramProvider,
    parse_metric_num,
    extract_meta_tag,
    extract_from_json_ld,
)
from app.services.reel_analytics_service import (
    calculate_reel_performance_metrics,
    _build_unavailable_metric,
)


def test_parse_metric_num_formats():
    assert parse_metric_num("123") == 123
    assert parse_metric_num("1,234") == 1234
    assert parse_metric_num("12.5K") == 12500
    assert parse_metric_num("1.2M") == 1200000
    assert parse_metric_num(" 450 ") == 450
    assert parse_metric_num("") is None
    assert parse_metric_num("invalid") is None


def test_extract_meta_tag_and_json_ld():
    sample_html = """
    <html>
      <head>
        <meta property="og:title" content="creator_pro on Instagram: &quot;Viral secrets for 2026&quot;" />
        <meta property="og:description" content="1,840 likes, 162 comments - creator_pro on November 13, 2026: &quot;Viral secrets for 2026&quot;" />
        <meta property="og:image" content="https://cdn.instagram.com/cover123.jpg" />
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "VideoObject",
          "name": "Viral secrets for 2026",
          "description": "Viral secrets for 2026",
          "thumbnailUrl": "https://cdn.instagram.com/cover123.jpg",
          "duration": "PT45S",
          "interactionStatistic": [
            {"@type": "InteractionCounter", "interactionType": "https://schema.org/LikeAction", "userInteractionCount": 1840},
            {"@type": "InteractionCounter", "interactionType": "https://schema.org/CommentAction", "userInteractionCount": 162},
            {"@type": "InteractionCounter", "interactionType": "https://schema.org/WatchAction", "userInteractionCount": 28450}
          ],
          "author": {"@type": "Person", "name": "creator_pro"}
        }
        </script>
      </head>
    </html>
    """
    assert extract_meta_tag(sample_html, "og:title") == 'creator_pro on Instagram: "Viral secrets for 2026"'
    assert extract_meta_tag(sample_html, "og:image") == 'https://cdn.instagram.com/cover123.jpg'

    import json
    json_ld_data = json.loads("""
    {
      "@type": "VideoObject",
      "name": "Viral secrets",
      "thumbnailUrl": "https://cdn.instagram.com/cover.jpg",
      "duration": "PT45S",
      "interactionStatistic": [
        {"@type": "InteractionCounter", "interactionType": "https://schema.org/LikeAction", "userInteractionCount": 1840},
        {"@type": "InteractionCounter", "interactionType": "https://schema.org/CommentAction", "userInteractionCount": 162},
        {"@type": "InteractionCounter", "interactionType": "https://schema.org/WatchAction", "userInteractionCount": 28450}
      ]
    }
    """)
    extracted = extract_from_json_ld(json_ld_data)
    assert extracted["likes"] == 1840
    assert extracted["comments"] == 162
    assert extracted["views"] == 28450
    assert extracted["duration_seconds"] == 45.0


def test_instagram_provider_metadata_extraction_with_public_metrics():
    provider = InstagramProvider()
    test_url = "https://www.instagram.com/reel/C8xyzABC123/"

    mock_oembed = {
        "title": "5 pacing tips that boosted my Reel retention",
        "author_name": "creator_pro",
        "thumbnail_url": "https://cdn.instagram.com/thumb_oembed.jpg",
        "width": 640,
        "height": 640,
    }
    mock_og = {
        "author": "creator_pro",
        "caption": "5 pacing tips that boosted my Reel retention",
        "thumbnail_url": "https://cdn.instagram.com/thumb_og.jpg",
        "likes": 1840,
        "comments": 162,
        "views": 28450,
        "duration_seconds": 32.5,
    }

    with patch.object(provider, "_fetch_meta_oembed", return_value=mock_oembed):
        with patch.object(provider, "_fetch_public_page_metadata", return_value=mock_og):
            meta = provider.extract_metadata(test_url)

            assert meta.platform == PlatformType.INSTAGRAM
            assert meta.video_id == "C8xyzABC123"
            assert meta.author == "creator_pro"
            assert "5 pacing tips" in (meta.caption or "")
            assert meta.views == 28450
            assert meta.likes == 1840
            assert meta.comments == 162
            assert meta.duration_seconds == 32.5
            assert meta.thumbnail_url == "https://cdn.instagram.com/thumb_oembed.jpg"


def test_instagram_provider_metadata_extraction_oembed_only():
    """When views/likes are not publicly exposed, oEmbed metadata is kept and metric counts remain None."""
    provider = InstagramProvider()
    test_url = "https://www.instagram.com/reel/C8xyzABC123/"

    mock_oembed = {
        "title": "Reel without public likes",
        "author_name": "private_counts_user",
        "thumbnail_url": "https://cdn.instagram.com/thumb.jpg",
    }

    with patch.object(provider, "_fetch_meta_oembed", return_value=mock_oembed):
        with patch.object(provider, "_fetch_public_page_metadata", return_value=None):
            meta = provider.extract_metadata(test_url)

            assert meta.platform == PlatformType.INSTAGRAM
            assert meta.video_id == "C8xyzABC123"
            assert meta.author == "private_counts_user"
            assert meta.caption == "Reel without public likes"
            assert meta.views is None
            assert meta.likes is None
            assert meta.comments is None


def test_instagram_provider_validate_access_webpage():
    provider = InstagramProvider()
    res = provider.validate_access("https://www.instagram.com/reel/C8xyzABC123/")
    assert res.allowed is False
    assert res.status == RetrievalStatus.CONNECT_ACCOUNT
    assert res.next_action == "CONNECT_INSTAGRAM"
    assert res.next_action_url == "/dashboard/instagram"
    assert "require authenticated access" in res.reason


def test_public_metadata_metric_calculation_measured_and_calculated():
    """Mode A analysis with public metadata calculates accurate rates and labels provenance."""
    perf = calculate_reel_performance_metrics(
        views=28450,
        likes=1840,
        comments=162,
        shares=None,
        saves=None,
        reach=None,
        video_duration_seconds=30.0,
        source_type="PUBLIC_METADATA",
    )

    # Measured counts
    assert perf["views"]["value"] == 28450.0
    assert perf["views"]["formatted"] == "28,450"
    assert perf["views"]["category"] == "MEASURED"
    assert "Public Video Metadata" in perf["views"]["source"]

    assert perf["likes"]["value"] == 1840.0
    assert perf["likes"]["formatted"] == "1,840"
    assert perf["likes"]["category"] == "MEASURED"
    assert "Public Video Metadata" in perf["likes"]["source"]

    assert perf["comments"]["value"] == 162.0
    assert perf["comments"]["formatted"] == "162"
    assert perf["comments"]["category"] == "MEASURED"
    assert "Public Video Metadata" in perf["comments"]["source"]

    # Derived rates
    assert perf["like_rate_views"]["category"] == "CALCULATED"
    assert perf["like_rate_views"]["value"] == round(1840 / 28450, 4)  # 0.0647
    assert perf["like_rate_views"]["formatted"] == "6.47%"

    assert perf["comment_rate"]["category"] == "CALCULATED"
    assert perf["comment_rate"]["value"] == round(162 / 28450, 4)  # 0.0057
    assert perf["comment_rate"]["formatted"] == "0.57%"

    # Engagement rate: (1840 + 162) / 28450 = 2002 / 28450 = 0.0704
    assert perf["engagement_rate"]["category"] == "CALCULATED"
    assert perf["engagement_rate"]["value"] == round(2002 / 28450, 4)  # 0.0704
    assert perf["engagement_rate"]["formatted"] == "7.04%"


def test_mode_c_private_metrics_remain_strictly_unavailable_with_clear_reason():
    """Private metrics must remain UNAVAILABLE in Mode A and explain that Mode C is required."""
    perf = calculate_reel_performance_metrics(
        views=28450,
        likes=1840,
        comments=162,
        shares=None,
        saves=None,
        reach=None,
        video_duration_seconds=30.0,
        source_type="PUBLIC_METADATA",
    )

    private_metrics = [
        "reach",
        "shares",
        "saves",
        "watch_ratio",
        "follow_conversion",
        "benchmark_delta",
        "like_rate_reach",
        "share_rate",
        "save_rate",
    ]

    for key in private_metrics:
        metric = perf[key]
        assert metric["value"] is None, f"{key} should be None"
        assert metric["category"] == "UNAVAILABLE", f"{key} category must be UNAVAILABLE"
        assert metric["formatted"] == "N/A", f"{key} formatted value must be N/A"
        assert metric["unavailable_reason"] == "Requires connected Instagram account", (
            f"{key} reason must be 'Requires connected Instagram account', got {metric.get('unavailable_reason')}"
        )


def test_missing_views_handling_rates_insufficient_data():
    """When views are unavailable, derived rates must be UNAVAILABLE with 'Insufficient data to calculate'."""
    perf = calculate_reel_performance_metrics(
        views=None,
        likes=1840,
        comments=162,
        shares=None,
        saves=None,
        reach=None,
        video_duration_seconds=30.0,
        source_type="PUBLIC_METADATA",
    )

    assert perf["views"]["value"] is None
    assert perf["views"]["category"] == "UNAVAILABLE"
    assert perf["views"]["unavailable_reason"] == "Not publicly available"

    # Likes and comments were measured
    assert perf["likes"]["value"] == 1840.0
    assert perf["likes"]["category"] == "MEASURED"

    assert perf["comments"]["value"] == 162.0
    assert perf["comments"]["category"] == "MEASURED"

    # Rates cannot be calculated without views
    assert perf["like_rate_views"]["value"] is None
    assert perf["like_rate_views"]["category"] == "UNAVAILABLE"
    assert perf["like_rate_views"]["unavailable_reason"] == "Insufficient data to calculate"

    assert perf["comment_rate"]["value"] is None
    assert perf["comment_rate"]["category"] == "UNAVAILABLE"
    assert perf["comment_rate"]["unavailable_reason"] == "Insufficient data to calculate"

    assert perf["engagement_rate"]["value"] is None
    assert perf["engagement_rate"]["category"] == "UNAVAILABLE"
    assert perf["engagement_rate"]["unavailable_reason"] == "Insufficient data to calculate"


def test_all_unavailable_when_no_public_metadata_extracted():
    """When an Instagram Reel yields zero public counts, all metrics have distinct honest reasons."""
    perf = calculate_reel_performance_metrics(
        views=None,
        likes=None,
        comments=None,
        shares=None,
        saves=None,
        reach=None,
        video_duration_seconds=0.0,
        source_type="UNAVAILABLE",
    )

    assert perf["views"]["unavailable_reason"] == "Not returned by source"
    assert perf["likes"]["unavailable_reason"] == "Not returned by source"
    assert perf["comments"]["unavailable_reason"] == "Not returned by source"
    assert perf["reach"]["unavailable_reason"] == "Requires connected Instagram account"
    assert perf["shares"]["unavailable_reason"] == "Requires connected Instagram account"
    assert perf["saves"]["unavailable_reason"] == "Requires connected Instagram account"
    assert perf["like_rate_views"]["unavailable_reason"] == "Insufficient data to calculate"
    assert perf["comment_rate"]["unavailable_reason"] == "Insufficient data to calculate"
    assert perf["engagement_rate"]["unavailable_reason"] == "Insufficient data to calculate"
