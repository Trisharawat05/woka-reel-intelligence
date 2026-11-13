import os
import json
import socket
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from app.services.video_ingestion import (
    PlatformType,
    RetrievalStatus,
    detect_platform,
    is_direct_video_url,
    get_provider_for_url,
    validate_video_url_safely,
    is_ip_private_or_restricted,
)
from app.services.video_ingestion.providers import (
    DirectVideoProvider,
    InstagramProvider,
    YouTubeProvider,
    TikTokProvider,
    FacebookProvider,
    VimeoProvider,
    GenericProvider,
)
from app.services.video_intelligence.video_processor import (
    validate_video_file_magic_bytes,
    classify_video_url_type,
    download_remote_video_with_diagnostics,
    _is_public_safe_video_url,
)
from app.services.video_intelligence.pipeline import run_video_intelligence_pipeline


# ---------------------------------------------------------------------------
# 1. Platform Detection Tests
# ---------------------------------------------------------------------------

def test_detect_instagram_urls():
    urls = [
        ("https://www.instagram.com/reel/C8xyzABC123/", "C8xyzABC123"),
        ("https://instagram.com/p/POST_456/", "POST_456"),
        ("https://instagr.am/reel/SHORT_789/?utm_source=ig", "SHORT_789"),
        ("https://www.instagram.com/tv/TV_000/", "TV_000"),
    ]
    for url, expected_id in urls:
        platform, vid_id = detect_platform(url)
        assert platform == PlatformType.INSTAGRAM
        assert vid_id == expected_id


def test_detect_youtube_urls():
    urls = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ&feature=share", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ]
    for url, expected_id in urls:
        platform, vid_id = detect_platform(url)
        assert platform == PlatformType.YOUTUBE
        assert vid_id == expected_id


def test_detect_tiktok_urls():
    urls = [
        ("https://www.tiktok.com/@creator/video/7123456789012345678", "7123456789012345678"),
        ("https://vm.tiktok.com/ZM8xyz123/", "ZM8xyz123"),
        ("https://vt.tiktok.com/ZS8xyz123/", "ZS8xyz123"),
        ("https://www.tiktok.com/t/ZT8xyz123/", "ZT8xyz123"),
    ]
    for url, expected_id in urls:
        platform, vid_id = detect_platform(url)
        assert platform == PlatformType.TIKTOK
        assert vid_id == expected_id


def test_detect_facebook_urls():
    urls = [
        ("https://www.facebook.com/reel/123456789012345", "123456789012345"),
        ("https://fb.watch/xyz123456/", "xyz123456"),
        ("https://www.facebook.com/watch/?v=987654321", "987654321"),
        ("https://www.facebook.com/page/videos/555444333/", "555444333"),
    ]
    for url, expected_id in urls:
        platform, vid_id = detect_platform(url)
        assert platform == PlatformType.FACEBOOK
        assert vid_id == expected_id


def test_detect_vimeo_urls():
    urls = [
        ("https://vimeo.com/76979871", "76979871"),
        ("https://www.vimeo.com/channels/staffpicks/76979871", "76979871"),
        ("https://player.vimeo.com/video/76979871", "76979871"),
    ]
    for url, expected_id in urls:
        platform, vid_id = detect_platform(url)
        assert platform == PlatformType.VIMEO
        assert vid_id == expected_id


def test_detect_direct_video_urls():
    urls = [
        "https://cdn.example.com/videos/promo.mp4",
        "https://storage.googleapis.com/my-bucket/clip.mov",
        "https://r2.cloudflarestorage.com/media/test.webm",
        "https://s3.amazonaws.com/media/video.mp4?AWSAccessKeyId=AKIAIOSFODNN7EXAMPLE&Signature=vjbyPxybdZaNmGa%2ByT272YEAiv4%3D&Expires=1700000000",
        "https://scontent-ams4-1.cdninstagram.com/v/t50.2886-16/clip.mp4?_nc_ht=scontent-ams4-1.cdninstagram.com",
    ]
    for url in urls:
        assert is_direct_video_url(url) is True
        platform, _ = detect_platform(url)
        assert platform == PlatformType.DIRECT_VIDEO


def test_detect_other_generic_urls():
    url = "https://example.com/articles/my-favorite-video"
    platform, _ = detect_platform(url)
    assert platform == PlatformType.OTHER


# ---------------------------------------------------------------------------
# 2. SSRF, URL Validation & Security Tests
# ---------------------------------------------------------------------------

def test_ssrf_rejects_localhost_and_private_ips():
    bad_urls = [
        "http://localhost:8000/video.mp4",
        "http://127.0.0.1/video.mp4",
        "http://192.168.1.100/video.mp4",
        "http://10.0.0.1/video.mp4",
        "http://172.16.0.1/video.mp4",
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://0.0.0.0/video.mp4",
        "http://[::1]/video.mp4",
    ]
    for bad_url in bad_urls:
        with pytest.raises(HTTPException) as exc_info:
            validate_video_url_safely(bad_url)
        assert exc_info.value.status_code == 422
        assert "forbidden" in exc_info.value.detail.lower() or "private" in exc_info.value.detail.lower()


def test_validate_video_url_safely_allows_public_urls():
    res = validate_video_url_safely("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert res["platform"] == "youtube"
    assert res["video_id"] == "dQw4w9WgXcQ"
    assert res["is_instagram"] is False

    res_ig = validate_video_url_safely("https://www.instagram.com/reel/C8xyzABC123/")
    assert res_ig["platform"] == "instagram"
    assert res_ig["video_id"] == "C8xyzABC123"
    assert res_ig["is_instagram"] is True
    assert res_ig["shortcode"] == "C8xyzABC123"


# ---------------------------------------------------------------------------
# 3. Pluggable Provider Architecture & Status System
# ---------------------------------------------------------------------------

def test_provider_registry_resolution():
    assert isinstance(get_provider_for_url("https://example.com/video.mp4"), DirectVideoProvider)
    assert isinstance(get_provider_for_url("https://www.instagram.com/reel/C8xyz123/"), InstagramProvider)
    assert isinstance(get_provider_for_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"), YouTubeProvider)
    assert isinstance(get_provider_for_url("https://www.tiktok.com/@user/video/12345"), TikTokProvider)
    assert isinstance(get_provider_for_url("https://www.facebook.com/reel/12345"), FacebookProvider)
    assert isinstance(get_provider_for_url("https://vimeo.com/76979871"), VimeoProvider)
    assert isinstance(get_provider_for_url("https://example.com/some/article"), GenericProvider)


def test_instagram_provider_webpage_requires_connected_account():
    provider = InstagramProvider()
    url = "https://www.instagram.com/reel/C8xyz123/"
    val = provider.validate_access(url)
    assert val.allowed is False
    assert val.status == RetrievalStatus.CONNECT_ACCOUNT
    assert val.next_action == "CONNECT_INSTAGRAM"
    assert val.next_action_url == "/dashboard/instagram"

    extraction = provider.retrieve_video(url)
    assert extraction.video_path is None
    assert extraction.retrieval_status == RetrievalStatus.CONNECT_ACCOUNT
    assert extraction.next_action == "CONNECT_INSTAGRAM"


def test_youtube_provider_returns_unsupported_with_upload_action():
    provider = YouTubeProvider()
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    val = provider.validate_access(url)
    assert val.allowed is False
    assert val.status == RetrievalStatus.UNSUPPORTED
    assert val.next_action == "UPLOAD_MP4"
    assert val.next_action_url == "#upload"

    extraction = provider.retrieve_video(url)
    assert extraction.video_path is None
    assert extraction.retrieval_status == RetrievalStatus.UNSUPPORTED
    assert extraction.next_action == "UPLOAD_MP4"
    assert "YouTube watch pages and Shorts do not provide raw MP4 video streams" in extraction.limitation_reason


def test_tiktok_provider_returns_unsupported_with_upload_action():
    provider = TikTokProvider()
    url = "https://www.tiktok.com/@creator/video/7123456789012345678"
    val = provider.validate_access(url)
    assert val.allowed is False
    assert val.status == RetrievalStatus.UNSUPPORTED
    assert val.next_action == "UPLOAD_MP4"


def test_facebook_provider_webpage_requires_connected_account():
    provider = FacebookProvider()
    url = "https://www.facebook.com/reel/123456789"
    val = provider.validate_access(url)
    assert val.allowed is False
    assert val.status == RetrievalStatus.CONNECT_ACCOUNT
    assert val.next_action == "CONNECT_INSTAGRAM"


def test_vimeo_provider_player_page_returns_unsupported():
    provider = VimeoProvider()
    url = "https://vimeo.com/76979871"
    val = provider.validate_access(url)
    assert val.allowed is False
    assert val.status == RetrievalStatus.UNSUPPORTED
    assert val.next_action == "UPLOAD_MP4"


# ---------------------------------------------------------------------------
# 4. Direct Video Download & Frame Decoding
# ---------------------------------------------------------------------------

def test_direct_video_provider_successful_retrieval(tmp_path):
    # Create valid synthetic MP4 file with 'ftyp'
    valid_mp4 = tmp_path / "valid.mp4"
    valid_mp4.write_bytes(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42" + b"\x00" * 1024)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "video/mp4"}
    mock_resp.url = "https://cdn.example.com/videos/valid.mp4"
    mock_resp.iter_bytes.return_value = [valid_mp4.read_bytes()]

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.stream.return_value.__enter__.return_value = mock_resp

    provider = DirectVideoProvider()
    url = "https://cdn.example.com/videos/valid.mp4"

    with patch("httpx.Client", return_value=mock_client), \
         patch("app.services.video_intelligence.video_processor._resolve_and_check_ssrf", return_value=True):
        extraction = provider.retrieve_video(url)
        assert extraction.retrieval_status == RetrievalStatus.VIDEO_RETRIEVED
        assert extraction.video_path is not None
        assert os.path.exists(extraction.video_path)
        # Clean up
        if os.path.exists(extraction.video_path):
            os.remove(extraction.video_path)


def test_direct_video_provider_auth_required():
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.headers = {"content-type": "text/html"}
    mock_resp.url = "https://s3.amazonaws.com/bucket/video.mp4?expired=1"

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.stream.return_value.__enter__.return_value = mock_resp

    provider = DirectVideoProvider()
    url = "https://s3.amazonaws.com/bucket/video.mp4?expired=1"

    with patch("httpx.Client", return_value=mock_client), \
         patch("app.services.video_intelligence.video_processor._resolve_and_check_ssrf", return_value=True):
        extraction = provider.retrieve_video(url)
        assert extraction.retrieval_status == RetrievalStatus.AUTH_REQUIRED
        assert extraction.video_path is None
        assert extraction.next_action == "LOGIN"


def test_generic_provider_rejects_html():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "text/html; charset=utf-8"}
    mock_resp.url = "https://example.com/player/video-123"
    mock_resp.iter_bytes.return_value = [b"<!DOCTYPE html><html><body>Video player</body></html>"]

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.stream.return_value.__enter__.return_value = mock_resp

    provider = GenericProvider()
    url = "https://example.com/player/video-123"

    with patch("httpx.Client", return_value=mock_client), \
         patch("app.services.video_intelligence.video_processor._resolve_and_check_ssrf", return_value=True):
        extraction = provider.retrieve_video(url)
        assert extraction.retrieval_status == RetrievalStatus.UNSUPPORTED
        assert extraction.video_path is None
        assert extraction.next_action == "UPLOAD_MP4"


def test_download_size_cap_enforced(tmp_path):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "video/mp4"}
    mock_resp.url = "https://cdn.example.com/huge.mp4"
    # Stream chunks totaling 26 MB (exceeding 25 MB cap)
    chunk = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * (1024 * 1024)
    mock_resp.iter_bytes.return_value = [chunk] * 26

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.stream.return_value.__enter__.return_value = mock_resp

    with patch("httpx.Client", return_value=mock_client), \
         patch("app.services.video_intelligence.video_processor._resolve_and_check_ssrf", return_value=True):
        path, source, reason = download_remote_video_with_diagnostics("https://cdn.example.com/huge.mp4")
        assert path is None
        assert source == "FILE_TOO_LARGE"
        assert "maximum download size cap" in reason


# ---------------------------------------------------------------------------
# 5. Full Pipeline & Metric Provenance Tests
# ---------------------------------------------------------------------------

def test_pipeline_no_fabricated_metrics_on_unsupported_url():
    """Verifies that an unsupported URL produces transparent 'Unavailable' metrics with 0 confidence."""
    video_intel = run_video_intelligence_pipeline(
        video_path=None,
        media_url=None,
        caption="Check out this video! #cool #trending",
        title="YouTube Video — dQw4w9WgXcQ",
        allow_simulation=False,
        source_identifier="dQw4w9WgXcQ",
    )
    assert video_intel["metadata"]["video_stream_analyzed"] is False
    assert video_intel["metadata"]["duration_seconds"] in (None, 0.0)
    assert video_intel["metadata"]["fps"] in (None, 0.0)
    assert video_intel["visual_pacing"]["cuts_detected"] in (None, 0)
    assert video_intel["visual_metrics"]["data_available"] is False


def test_pipeline_real_opencv_decoding_with_synthetic_video(tmp_path):
    """Verifies that real decoded video yields actual measured FPS, duration, resolution, and aspect ratio."""
    try:
        import cv2
    except ImportError:
        pytest.skip("OpenCV not installed in test environment")

    # Write a real short video file using OpenCV
    video_file = str(tmp_path / "real_video.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(video_file, fourcc, 30.0, (720, 1280))

    for i in range(45):  # 1.5 seconds at 30 fps
        color = (255, 0, 0) if i < 20 else (0, 255, 0)
        frame = np.full((1280, 720, 3), color, dtype=np.uint8)
        out.write(frame)
    out.release()

    video_intel = run_video_intelligence_pipeline(
        video_path=video_file,
        caption="Testing video decode",
        title="Decoded Video Test",
        output_thumbnail_dir=str(tmp_path / "thumbnails"),
        allow_simulation=False,
    )

    meta = video_intel["metadata"]
    assert meta["video_stream_analyzed"] is True
    assert meta["width"] == 720
    assert meta["height"] == 1280
    assert meta["aspect_ratio"] == "9:16"
    assert meta["fps"] == pytest.approx(30.0, abs=2.0)
    assert meta["duration_seconds"] == pytest.approx(1.5, abs=0.3)
    assert video_intel["visual_metrics"]["data_available"] is True
