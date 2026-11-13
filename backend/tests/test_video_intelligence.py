import os
import tempfile
import pytest
import cv2
import numpy as np
from unittest.mock import MagicMock, patch

from app.config import settings
from app.services.video_intelligence import video_processor
from app.services.video_intelligence.video_processor import (
    validate_video_file_magic_bytes,
    classify_video_url_type,
    _is_public_safe_video_url,
    download_remote_video_to_temp,
    download_remote_video_with_diagnostics,
    extract_video_metadata_and_frames,
    unavailable_video_metrics,
)
from app.services.video_intelligence.pipeline import run_video_intelligence_pipeline
from app.services.reel_intelligence_service import validate_instagram_reel_url


def _create_synthetic_mp4(
    path: str,
    width: int = 180,
    height: int = 320,
    fps: float = 30.0,
    num_frames: int = 30,
    has_cut: bool = False,
) -> str:
    """Helper to create a small valid MP4 video using OpenCV VideoWriter."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(path, fourcc, fps, (width, height))
    for i in range(num_frames):
        if has_cut and i >= (num_frames // 2):
            frame = np.full((height, width, 3), [0, 255, 100], dtype=np.uint8)
        else:
            frame = np.full((height, width, 3), [255, 120, 0], dtype=np.uint8)
        out.write(frame)
    out.release()
    return path


# ---------------------------------------------------------------------------
# 1. Public Direct MP4 URL Download
# ---------------------------------------------------------------------------
def test_valid_downloadable_video_file(monkeypatch, tmp_path):
    monkeypatch.setattr(video_processor, "_resolve_and_check_ssrf", lambda host: True)

    valid_mp4_header = b"\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp42isom"
    dummy_payload = valid_mp4_header + (b"\xaa" * 2000)

    class MockStreamResponse:
        status_code = 200
        url = "https://scontent.cdninstagram.com/v/t50.2886-16/valid_reel.mp4"
        headers = {"content-type": "video/mp4"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def iter_bytes(self, chunk_size=262144):
            yield dummy_payload

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def stream(self, method, url):
            return MockStreamResponse()

    monkeypatch.setattr("httpx.Client", MockClient)

    tmp, source, lim = download_remote_video_with_diagnostics(
        "https://scontent.cdninstagram.com/v/t50.2886-16/valid_reel.mp4"
    )
    assert tmp is not None
    assert source == "OPENCV_REMOTE_STREAM"
    assert lim is None
    assert os.path.exists(tmp)

    try:
        with open(tmp, "rb") as f:
            header = f.read(64)
        assert validate_video_file_magic_bytes(header) is True
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ---------------------------------------------------------------------------
# 2. Valid Video Redirects (followed up to 5 hops)
# ---------------------------------------------------------------------------
def test_redirect_to_valid_video(monkeypatch):
    monkeypatch.setattr(video_processor, "_resolve_and_check_ssrf", lambda host: True)

    valid_mp4_header = b"\x00\x00\x00\x18ftypmp42" + (b"\x00" * 8)
    dummy_payload = valid_mp4_header + (b"\xbb" * 1000)

    class MockRedirectedResponse:
        status_code = 200
        url = "https://scontent.cdninstagram.com/v/t50.2886-16/redirected_final.mp4"
        headers = {"content-type": "video/mp4"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def iter_bytes(self, chunk_size=262144):
            yield dummy_payload

    class MockClient:
        def __init__(self, follow_redirects=None, max_redirects=None, **kwargs):
            assert follow_redirects is True
            assert max_redirects == 5

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def stream(self, method, url):
            return MockRedirectedResponse()

    monkeypatch.setattr("httpx.Client", MockClient)

    downloaded, source, lim = download_remote_video_with_diagnostics(
        "https://scontent.cdninstagram.com/v/t50.2886-16/initial.mp4"
    )
    assert downloaded is not None
    assert source == "OPENCV_REMOTE_STREAM"
    assert lim is None
    assert os.path.exists(downloaded)
    os.remove(downloaded)


# ---------------------------------------------------------------------------
# 3. Invalid or Private Redirect Destinations (SSRF protection on redirect)
# ---------------------------------------------------------------------------
def test_redirect_to_private_destination_blocked(monkeypatch):
    class MockPrivateRedirectResponse:
        status_code = 200
        url = "http://169.254.169.254/latest/meta-data/video.mp4"
        headers = {"content-type": "video/mp4"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def iter_bytes(self, chunk_size=262144):
            yield b"\x00\x00\x00\x20ftypmp42" + (b"\x00" * 500)

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def stream(self, method, url):
            return MockPrivateRedirectResponse()

    monkeypatch.setattr("httpx.Client", MockClient)

    tmp, source, lim = download_remote_video_with_diagnostics(
        "https://scontent.cdninstagram.com/v/t50.2886-16/redirect_to_private.mp4"
    )
    assert tmp is None
    assert source == "SSRF_REDIRECT_BLOCKED"
    assert "private" in (lim or "").lower() or "internal" in (lim or "").lower()


# ---------------------------------------------------------------------------
# 4. Instagram Webpage URL (Classified, rejected with Mode B/C recommendation)
# ---------------------------------------------------------------------------
def test_instagram_webpage_url_classified_and_rejected():
    url = "https://www.instagram.com/reel/C1234567890/?igsh=abc123xyz"
    assert classify_video_url_type(url) == "INSTAGRAM_PAGE"

    tmp, source, lim = download_remote_video_with_diagnostics(url)
    assert tmp is None
    assert source == "INSTAGRAM_PAGE_UNSUPPORTED"
    assert "Mode B" in (lim or "")
    assert "Mode C" in (lim or "")


# ---------------------------------------------------------------------------
# 5. HTML Returned Instead of Video
# ---------------------------------------------------------------------------
def test_html_response_rejected(monkeypatch):
    monkeypatch.setattr(video_processor, "_resolve_and_check_ssrf", lambda host: True)

    # 5a: text/html header rejected
    class MockHtmlHeaderResponse:
        status_code = 200
        url = "https://scontent.cdninstagram.com/v/t50.2886-16/fake.mp4"
        headers = {"content-type": "text/html; charset=utf-8"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def iter_bytes(self, chunk_size=262144):
            yield b"<!DOCTYPE html><html><body>Login</body></html>"

    class MockClientHtmlHeader:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def stream(self, method, url):
            return MockHtmlHeaderResponse()

    monkeypatch.setattr("httpx.Client", MockClientHtmlHeader)
    tmp, source, lim = download_remote_video_with_diagnostics("https://scontent.cdninstagram.com/v/t50.2886-16/fake.mp4")
    assert tmp is None
    assert source == "HTML_RESPONSE_NOT_VIDEO"
    assert "HTML" in (lim or "")

    # 5b: Content-type claims video/mp4 but first chunk is HTML
    class MockHtmlBodyResponse:
        status_code = 200
        url = "https://scontent.cdninstagram.com/v/t50.2886-16/disguised.mp4"
        headers = {"content-type": "video/mp4"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def iter_bytes(self, chunk_size=262144):
            yield b"<!DOCTYPE html><html lang='en'><head><title>Instagram</title></head><body>Login required" + (b" " * 200)

    class MockClientHtmlBody:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def stream(self, method, url):
            return MockHtmlBodyResponse()

    monkeypatch.setattr("httpx.Client", MockClientHtmlBody)
    tmp, source, lim = download_remote_video_with_diagnostics("https://scontent.cdninstagram.com/v/t50.2886-16/disguised.mp4")
    assert tmp is None
    assert source == "HTML_RESPONSE_NOT_VIDEO"


# ---------------------------------------------------------------------------
# 6. Instagram URL Requiring Authentication (401 / 403)
# ---------------------------------------------------------------------------
def test_instagram_url_requiring_authentication(monkeypatch):
    monkeypatch.setattr(video_processor, "_resolve_and_check_ssrf", lambda host: True)

    class Mock403Response:
        status_code = 403
        url = "https://scontent.cdninstagram.com/v/t50.2886-16/expired_signature.mp4"
        headers = {"content-type": "text/plain"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def iter_bytes(self, chunk_size=262144):
            yield b"URL signature expired"

    class MockClient403:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def stream(self, method, url):
            return Mock403Response()

    monkeypatch.setattr("httpx.Client", MockClient403)
    tmp, source, lim = download_remote_video_with_diagnostics(
        "https://scontent.cdninstagram.com/v/t50.2886-16/expired_signature.mp4"
    )
    assert tmp is None
    assert source == "HTTP_AUTH_REQUIRED"
    assert "HTTP 403" in (lim or "")


# ---------------------------------------------------------------------------
# 7. Private Inaccessible Reel (404)
# ---------------------------------------------------------------------------
def test_private_inaccessible_reel(monkeypatch):
    monkeypatch.setattr(video_processor, "_resolve_and_check_ssrf", lambda host: True)

    class Mock404Response:
        status_code = 404
        url = "https://scontent.cdninstagram.com/v/t50.2886-16/not_found.mp4"
        headers = {"content-type": "application/json"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def iter_bytes(self, chunk_size=262144):
            yield b'{"error": "Not found"}'

    class MockClient404:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def stream(self, method, url):
            return Mock404Response()

    monkeypatch.setattr("httpx.Client", MockClient404)
    tmp, source, lim = download_remote_video_with_diagnostics(
        "https://scontent.cdninstagram.com/v/t50.2886-16/not_found.mp4"
    )
    assert tmp is None
    assert source == "HTTP_NOT_FOUND"


# ---------------------------------------------------------------------------
# 8. Invalid Video File Magic Bytes
# ---------------------------------------------------------------------------
def test_invalid_video_file_magic_bytes():
    assert validate_video_file_magic_bytes(b"MZ\x90\x00" + b"\x00" * 40) is False
    assert validate_video_file_magic_bytes(b"\x7fELF" + b"\x00" * 40) is False
    assert validate_video_file_magic_bytes(b"#!/bin/bash\nrm -rf /") is False
    assert validate_video_file_magic_bytes(b"<?php echo 'bad'; ?>") is False
    assert validate_video_file_magic_bytes(b"<!DOCTYPE html><html>") is False
    assert validate_video_file_magic_bytes(b"<html><head><title>") is False
    assert validate_video_file_magic_bytes(b"") is False
    assert validate_video_file_magic_bytes(b"mp4") is False

    assert validate_video_file_magic_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 30) is True
    assert validate_video_file_magic_bytes(b"\x00\x00\x00\x14ftypqt  " + b"\x00" * 30) is True
    assert validate_video_file_magic_bytes(b"\x1a\x45\xdf\xa3" + b"\x00" * 30) is True


# ---------------------------------------------------------------------------
# 9. Unsupported Video Extraction (Missing OpenCV Decoder)
# ---------------------------------------------------------------------------
def test_opencv_decoder_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(video_processor, "HAS_OPENCV", False)

    dummy_video = os.path.join(str(tmp_path), "test.mp4")
    with open(dummy_video, "wb") as f:
        f.write(b"\x00\x00\x00\x18ftypmp42" + (b"\x00" * 200))

    res = extract_video_metadata_and_frames(
        video_path=dummy_video,
        output_thumbnail_dir=str(tmp_path),
        allow_simulation=False,
    )

    assert res["video_stream_analyzed"] is False
    assert res["video_source"] == "DECODER_UNAVAILABLE"
    assert res["duration_measured"] is False
    assert "OpenCV" in (res.get("limitation") or "")


# ---------------------------------------------------------------------------
# 10. Successful Real Frame Decoding
# ---------------------------------------------------------------------------
def test_successful_real_frame_decoding(tmp_path):
    video_path = os.path.join(str(tmp_path), "real_video.mp4")
    _create_synthetic_mp4(
        video_path,
        width=180,
        height=320,
        fps=30.0,
        num_frames=30,
        has_cut=True,
    )

    res = extract_video_metadata_and_frames(
        video_path=video_path,
        output_thumbnail_dir=str(tmp_path),
        allow_simulation=False,
    )

    assert res["video_stream_analyzed"] is True
    assert res["sampled_frame_count"] > 0
    assert res["resolution_width"] == 180
    assert res["resolution_height"] == 320
    assert res["thumbnail_filename"] is not None

    thumb_full = os.path.join(str(tmp_path), res["thumbnail_filename"])
    assert os.path.exists(thumb_full)


# ---------------------------------------------------------------------------
# 11. Duration, FPS, Resolution Measurement
# ---------------------------------------------------------------------------
def test_duration_fps_resolution_measurement(tmp_path):
    video_path = os.path.join(str(tmp_path), "measure_video.mp4")
    _create_synthetic_mp4(
        video_path,
        width=180,
        height=320,
        fps=30.0,
        num_frames=60,  # 2.0 seconds at 30 fps
    )

    res = extract_video_metadata_and_frames(
        video_path=video_path,
        output_thumbnail_dir=str(tmp_path),
        allow_simulation=False,
    )

    assert res["duration_measured"] is True
    assert abs(res["duration_seconds"] - 2.0) < 0.2
    assert res["fps_measured"] is True
    assert res["fps"] == 30.0
    assert res["aspect_ratio"] == "9:16"
    assert res["is_safe_vertical"] is True


# ---------------------------------------------------------------------------
# 12. Audio Extraction Failure Handled Gracefully
# ---------------------------------------------------------------------------
def test_audio_extraction_failure_graceful(tmp_path, monkeypatch):
    video_path = os.path.join(str(tmp_path), "no_audio.mp4")
    _create_synthetic_mp4(video_path, num_frames=15)

    def mock_extract_audio_fail(path, output_dir):
        raise RuntimeError("Simulated FFmpeg audio failure")

    monkeypatch.setattr(
        video_processor, "extract_audio_with_ffmpeg", mock_extract_audio_fail
    )

    res = extract_video_metadata_and_frames(
        video_path=video_path,
        output_thumbnail_dir=str(tmp_path),
        allow_simulation=False,
    )

    assert res["video_stream_analyzed"] is True
    assert res["audio_extracted"] is False


# ---------------------------------------------------------------------------
# 13. Temporary File Lifecycle & Cleanup
# ---------------------------------------------------------------------------
def test_temporary_file_cleanup(tmp_path, monkeypatch):
    temp_video = os.path.join(str(tmp_path), "stream_temp_123.mp4")
    _create_synthetic_mp4(temp_video, num_frames=15)
    assert os.path.exists(temp_video)

    monkeypatch.setattr(
        video_processor,
        "download_remote_video_with_diagnostics",
        lambda url: (temp_video, "OPENCV_REMOTE_STREAM", None),
    )

    res = extract_video_metadata_and_frames(
        video_path=None,
        media_url="https://scontent.cdninstagram.com/v/t50.2886-16/test.mp4",
        output_thumbnail_dir=str(tmp_path),
        allow_simulation=False,
    )

    assert res["video_stream_analyzed"] is True
    assert not os.path.exists(temp_video)


# ---------------------------------------------------------------------------
# 14. SSRF Protection (Localhost, Private IPs, Metadata)
# ---------------------------------------------------------------------------
def test_ssrf_protection():
    blocked_urls = [
        "http://localhost/video.mp4",
        "http://127.0.0.1:8000/video.mp4",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.1/video.mp4",
        "http://192.168.1.1/video.mp4",
        "http://[::1]/video.mp4",
        "http://service.internal/video.mp4",
    ]

    for url in blocked_urls:
        assert classify_video_url_type(url) == "BLOCKED", f"Failed for {url}"
        assert _is_public_safe_video_url(url) is False, f"Failed for {url}"


# ---------------------------------------------------------------------------
# 15. Partial Analysis on Text-Only / Unsupported Reel Page
# ---------------------------------------------------------------------------
def test_partial_analysis_text_only(tmp_path):
    pipeline_result = run_video_intelligence_pipeline(
        video_path=None,
        media_url="https://www.instagram.com/reel/C1234567890/",
        caption="Check out these 3 productivity tips! #productivity #growth #tips",
        allow_simulation=False,
        output_thumbnail_dir=str(tmp_path),
    )

    assert pipeline_result["metadata"]["video_stream_analyzed"] is False
    assert pipeline_result["metadata"]["duration_measured"] is False
    assert pipeline_result["text_context"]["caption_present"] is True
    assert len(pipeline_result["text_context"]["full_text"]) > 0
    assert len(pipeline_result["text_context"]["hashtags"]) >= 3
    assert "hook_score" in pipeline_result["hook_analysis"]


# ---------------------------------------------------------------------------
# 16. No Fabricated Metrics When Video Is Unavailable
# ---------------------------------------------------------------------------
def test_no_fabricated_metrics(tmp_path):
    pipeline_result = run_video_intelligence_pipeline(
        video_path=None,
        media_url="https://www.instagram.com/reel/C9999999999/",
        allow_simulation=False,
        output_thumbnail_dir=str(tmp_path),
    )

    meta = pipeline_result["metadata"]
    assert meta["video_stream_analyzed"] is False
    assert meta["duration_measured"] is False
    assert meta["duration_seconds"] in (None, 0.0)
    assert meta["is_simulated"] is False
    assert meta["limitation"] is not None

    pacing = pipeline_result["visual_pacing"]
    assert pacing["cuts_detected"] in (None, 0)


# ---------------------------------------------------------------------------
# 17. Direct Video URL Validation with Query Strings
# ---------------------------------------------------------------------------
def test_direct_video_url_validation_with_query_params():
    url_with_query = "https://cdn.example.com/clips/reel_export.mp4?expires=1730000000&token=sec_abc123"
    validated = validate_instagram_reel_url(url_with_query)
    assert validated["is_instagram"] is False
    assert validated["url"] == url_with_query

    # Also validates instagr.am short links
    ig_short = "https://instagr.am/reel/DCEmailShort123/"
    validated_ig = validate_instagram_reel_url(ig_short)
    assert validated_ig["is_instagram"] is True
    assert validated_ig["shortcode"] == "DCEmailShort123"


# ---------------------------------------------------------------------------
# 18. Public Direct MP4 URL End-to-End Decoded
# ---------------------------------------------------------------------------
def test_public_direct_mp4_url_end_to_end_decoded(tmp_path, monkeypatch):
    synthetic_video = os.path.join(str(tmp_path), "downloaded_stream.mp4")
    _create_synthetic_mp4(synthetic_video, width=540, height=960, fps=30.0, num_frames=30)

    # Mock download_remote_video_with_diagnostics to return this valid MP4
    monkeypatch.setattr(
        video_processor,
        "download_remote_video_with_diagnostics",
        lambda url: (synthetic_video, "OPENCV_REMOTE_STREAM", None),
    )

    result = run_video_intelligence_pipeline(
        video_path=None,
        media_url="https://cdn.example.com/videos/public_reel.mp4",
        output_thumbnail_dir=str(tmp_path),
        allow_simulation=False,
    )

    assert result["metadata"]["video_stream_analyzed"] is True
    assert result["metadata"]["duration_measured"] is True
    assert result["metadata"]["fps"] == 30.0
    assert result["metadata"]["width"] == 540
    assert result["metadata"]["height"] == 960
    assert result["metadata"]["aspect_ratio"] == "9:16"
    assert result["visual_metrics"]["data_available"] is True
