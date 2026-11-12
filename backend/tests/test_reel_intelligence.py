import pytest
from app.services.reel_analytics_service import (
    calculate_reel_performance_metrics,
    classify_benchmark_status
)
from app.services.video_intelligence.audio_processor import analyze_audio_and_speech
from app.services.video_intelligence.pipeline import run_video_intelligence_pipeline
from app.services.reel_ai_diagnosis_service import generate_ai_diagnosis_report
from app.services.reel_intelligence_service import execute_reel_analysis
from app.models.reel_intelligence import ReelAnalysisJob, ReelReport
from app.security import create_access_token, get_password_hash
from app.models.user import User, Workspace, WorkspaceMember


def test_metric_calculation_formulas_standard():
    """Validates math formulas for like rate, comment rate, save rate, and engagement rate."""
    views = 10000
    likes = 500
    comments = 50
    shares = 100
    saves = 200
    reach = 8000
    avg_watch = 18.0
    duration = 24.0

    metrics = calculate_reel_performance_metrics(
        views=views,
        likes=likes,
        comments=comments,
        shares=shares,
        saves=saves,
        reach=reach,
        avg_watch_time=avg_watch,
        video_duration_seconds=duration,
        source_type="META_GRAPH_API"
    )

    # Like Rate: 500 / 10000 = 0.05 (5.0%)
    assert metrics["like_rate_views"]["value"] == 0.05
    assert metrics["like_rate_views"]["formatted"] == "5.0%"

    # Comment Rate: 50 / 10000 = 0.005 (0.5%)
    assert metrics["comment_rate"]["value"] == 0.005
    assert metrics["comment_rate"]["formatted"] == "0.5%"

    # Share Rate: 100 / 10000 = 0.01 (1.0%)
    assert metrics["share_rate"]["value"] == 0.01

    # Save Rate: 200 / 10000 = 0.02 (2.0%)
    assert metrics["save_rate"]["value"] == 0.02

    # Engagement Rate (Reach-based): (500 + 50 + 100 + 200) / 8000 = 850 / 8000 = 0.10625 -> 0.1062 (10.62%)
    assert metrics["engagement_rate"]["value"] == 0.1062
    assert "Reach" in metrics["engagement_rate"]["name"]

    # Watch Ratio: 18.0 / 24.0 = 0.75 (75.0%)
    assert metrics["watch_ratio"]["value"] == 0.75
    assert metrics["watch_ratio"]["formatted"] == "75.0%"


def test_metric_calculation_zero_views_and_missing_reach_edge_case():
    """Ensures division by zero is safely prevented when views or reach are zero or None."""
    metrics = calculate_reel_performance_metrics(
        views=0,
        likes=0,
        comments=0,
        shares=0,
        saves=0,
        reach=None,
        source_type="PUBLIC_SCRAPE_FALLBACK"
    )

    assert metrics["views"]["value"] == 0.0
    assert metrics["like_rate_views"]["value"] == 0.0
    assert metrics["reach"]["value"] is None
    assert "Connected Account Only" in metrics["watch_ratio"]["formatted"]


def test_audio_speech_wpm_and_dead_air():
    """Validates WPM calculation and dead-air pause detection."""
    # 50 words spoken in 20 seconds = 150 WPM
    words_50 = " ".join(["word"] * 50)
    audio = analyze_audio_and_speech(words_50, duration_seconds=20.0)

    assert audio["words_per_minute"] == 150.0
    assert audio["pacing_rating"] == "OPTIMAL_ENERGY"

    # Dead air simulated when word density is very low for long duration
    slow_words = "stop and wait"
    audio_slow = analyze_audio_and_speech(slow_words, duration_seconds=30.0)
    assert audio_slow["dead_air_count"] >= 1
    assert audio_slow["pacing_rating"] == "SLOW_DRAG"


def test_ai_diagnosis_scoring_ranges_and_components():
    """Verifies that all 4 scores fall strictly within [0, 100] with populated components."""
    video_intel = run_video_intelligence_pipeline(
        caption="Stop doing this mistake on Instagram reels. Comment GUIDE for the free blueprint!"
    )
    perf_metrics = calculate_reel_performance_metrics(
        views=15000,
        likes=900,
        comments=80,
        shares=140,
        saves=320,
        source_type="PUBLIC_SCRAPE_FALLBACK"
    )

    report = generate_ai_diagnosis_report(
        video_intel=video_intel,
        performance_metrics=perf_metrics,
        analysis_mode="PUBLIC_URL"
    )

    scores = report["scores"]
    assert 0 <= scores["creative_quality"]["score"] <= 100
    assert 0 <= scores["performance"]["score"] <= 100
    assert 0 <= scores["growth_conversion"]["score"] <= 100
    assert 0 <= scores["viral_potential"]["score"] <= 100

    assert len(scores["creative_quality"]["components"]) == 5
    assert len(report["timeline_findings"]) >= 3
    assert len(report["prioritized_action_plan"]) == 3
    assert len(report["creative_alternatives"]["alternative_hooks"]) >= 3


def test_api_submit_public_url_job_and_poll_status(client, auth_headers):
    """Integration test: submits a public Reel URL and polls its execution status."""
    payload = {
        "url": "https://www.instagram.com/reel/C8xyzABC123/",
        "declared_views": 18500,
        "declared_likes": 1200,
        "declared_comments": 85
    }

    # 1. Submit Job
    res = client.post("/api/v1/reel-intelligence/jobs/url", json=payload, headers=auth_headers)
    assert res.status_code == 202
    job_data = res.json()
    job_id = job_data["id"]
    assert job_data["analysis_mode"] == "PUBLIC_URL"
    assert job_data["input_type"] == "url"

    # 2. Poll Status
    status_res = client.get(f"/api/v1/reel-intelligence/jobs/{job_id}", headers=auth_headers)
    assert status_res.status_code == 200
    assert status_res.json()["id"] == job_id


def test_api_submit_connected_reel_and_fetch_report(client, auth_headers, db_session):
    """Integration test: submits a connected Reel, executes analysis, and retrieves full report."""
    payload = {
        "media_id": "ig_reel_ig_test_user_id_101",
        "title": "3 Pacing Secrets for Creators",
        "caption": "Why you need to cut breaths and dead air. Comment BLUEPRINT below!"
    }

    # Submit
    res = client.post("/api/v1/reel-intelligence/jobs/connected", json=payload, headers=auth_headers)
    assert res.status_code == 202
    job_id = res.json()["id"]

    # Poll status -> TestClient executes BackgroundTasks before return, so status is COMPLETED
    poll = client.get(f"/api/v1/reel-intelligence/jobs/{job_id}", headers=auth_headers)
    assert poll.status_code == 200
    assert poll.json()["status"] == "COMPLETED", f"Job failed: {poll.json().get('error_message')}"
    report_id = poll.json()["report_id"]
    assert report_id is not None

    # Retrieve Full Report
    rep = client.get(f"/api/v1/reel-intelligence/reports/{report_id}", headers=auth_headers)
    assert rep.status_code == 200
    rep_data = rep.json()
    assert rep_data["id"] == report_id
    assert "scores" in rep_data
    assert "calculated_metrics" in rep_data
    assert "timeline_findings" in rep_data
    assert "prioritized_action_plan" in rep_data
    assert "creative_alternatives" in rep_data


def test_api_compare_reels(client, auth_headers, db_session):
    """Integration test: compares 2 completed Reel reports."""
    # Create two completed reports
    job1_res = client.post("/api/v1/reel-intelligence/jobs/connected", json={"media_id": "ig_reel_ig_test_user_id_101"}, headers=auth_headers)
    job2_res = client.post("/api/v1/reel-intelligence/jobs/connected", json={"media_id": "ig_reel_ig_test_user_id_102"}, headers=auth_headers)
    
    id1 = job1_res.json()["id"]
    id2 = job2_res.json()["id"]

    r1_id = client.get(f"/api/v1/reel-intelligence/jobs/{id1}", headers=auth_headers).json()["report_id"]
    r2_id = client.get(f"/api/v1/reel-intelligence/jobs/{id2}", headers=auth_headers).json()["report_id"]

    comp_res = client.post(
        "/api/v1/reel-intelligence/compare",
        json={"report_ids": [r1_id, r2_id]},
        headers=auth_headers
    )
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert len(comp_data["reports"]) == 2
    assert comp_data["winner_id"] in [r1_id, r2_id]
    assert len(comp_data["comparative_takeaways"]) > 0


def test_multi_tenant_job_isolation(client, db_session, test_creator_user):
    """Ensures another tenant cannot inspect or fetch reports belonging to another workspace."""
    _, creator_ws = test_creator_user

    # Create second tenant
    other_user = User(
        email="hacker@other.io",
        hashed_password=get_password_hash("OtherPass123!"),
        full_name="Other User",
        role="CREATOR"
    )
    db_session.add(other_user)
    db_session.flush()

    other_ws = Workspace(name="Other Workspace", owner_id=other_user.id)
    db_session.add(other_ws)
    db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=other_ws.id, user_id=other_user.id, role_in_workspace="OWNER"))
    db_session.commit()

    other_token = create_access_token(data={"sub": other_user.id, "role": other_user.role, "workspace_id": other_ws.id})
    other_headers = {"Authorization": f"Bearer {other_token}"}

    # Creator creates a job
    creator_token = create_access_token(data={"sub": test_creator_user[0].id, "role": "CREATOR", "workspace_id": creator_ws.id})
    creator_headers = {"Authorization": f"Bearer {creator_token}"}

    job_res = client.post(
        "/api/v1/reel-intelligence/jobs/url",
        json={"url": "https://www.instagram.com/reel/C123Private/"},
        headers=creator_headers
    )
    job_id = job_res.json()["id"]

    # Other tenant attempts to read Creator's job -> 404 NOT FOUND
    forbidden_res = client.get(f"/api/v1/reel-intelligence/jobs/{job_id}", headers=other_headers)
    assert forbidden_res.status_code == 404


def test_invalid_url_validation_rejection(client, auth_headers):
    """Ensures non-video / invalid URLs are rejected with 422 Unprocessable Entity."""
    res = client.post(
        "/api/v1/reel-intelligence/jobs/url",
        json={"url": "not-a-valid-url-format"},
        headers=auth_headers
    )
    assert res.status_code == 422


def test_ssrf_and_private_network_rejection(client, auth_headers):
    """Ensures SSRF attacks targeting localhost, loopback, or private networks are blocked."""
    private_targets = [
        "http://127.0.0.1/video.mp4",
        "http://127.0.0.1:8000/api/v1/users",
        "http://169.254.169.254/latest/meta-data",
        "http://localhost/exploit.mp4",
        "http://0.0.0.0/test.mp4",
        "ftp://instagram.com/reel/C123/"
    ]
    for target in private_targets:
        res = client.post(
            "/api/v1/reel-intelligence/jobs/url",
            json={"url": target},
            headers=auth_headers
        )
        assert res.status_code == 422, f"Target {target} should have been rejected with 422"


def generate_minimal_mp4_bytes() -> bytes:
    """
    Generates a genuinely valid, decodable, minimal MP4 container with valid ftyp, moov, and mdat atoms.
    Attempts dynamic generation with OpenCV if available, or falls back to a deterministic 919-byte 1-frame MP4.
    """
    try:
        import cv2
        import numpy as np
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(tmp_path, fourcc, 10.0, (64, 64))
            out.write(np.zeros((64, 64, 3), dtype=np.uint8))
            out.release()
            with open(tmp_path, "rb") as f:
                content = f.read()
            if content and b"moov" in content and b"ftyp" in content:
                return content
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception:
        pass

    import base64
    return base64.b64decode(
        "AAAAHGZ0eXBpc29tAAACAGlzb21pc28ybXA0MQAAAAhmcmVlAAAAQ21kYXQAAAGzABAHAAABthDA4wR7b+Ntv422/jbb+Ntv422"
        "/jbb+Ntv422/jbb+Ntv422/jbb+Ntv422/jbb9wAAAzBtb292AAAAbG12aGQAAAAAAAAAAAAAAAAAAAPoAAAAZAABAAABAAAAAA"
        "AAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAAACW3"
        "RyYWsAAABcdGtoZAAAAAMAAAAAAAAAAAAAAAEAAAAAAAAAZAAAAAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAEAAAAAAAA"
        "AAAAAAAAAAEAAAAAAQAAAAEAAAAAAACRlZHRzAAAAHGVsc3QAAAAAAAAAAQAAAGQAAAAAAAEAAAAAAdNtZGlhAAAAIG1kaGQAAAA"
        "AAAAAAAAAAAAAACgAAAAEAFXEAAAAAAAtaGRscgAAAAAAAAAAdmlkZQAAAAAAAAAAAAAAAFZpZGVvSGFuZGxlcgAAAAF+bWluZgA"
        "AABR2bWhkAAAAAQAAAAAAAAAAAAAAJGRpbmYAAAAcZHJlZgAAAAAAAAABAAAADHVybCAAAAABAAABPnN0YmwAAADac3RzZAAAAAA"
        "AAAABAAAAym1wNHYAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAQABAAEgAAABIAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAY//8AAABgZXNkcwAAAAADgICATwABAASAgIBBIBEAAAAAAUAAAAAScAWAgIAvAAABsAEAAAG1iRMAAAEAAA"
        "ABIADEjYgAVQIECBRjAAABskxhdmM2MS4xOS4xMDAGgICAAQIAAAAUYnRydAAAAAAAAUAAAAAScAAAABhzdHRzAAAAAAAAAAEAA"
        "AABAAAEAAAAABxzdHNjAAAAAAAAAAEAAAABAAAAAQAAAAEAAAAUc3RzegAAAAAAAAA7AAAAAQAAABRzdGNvAAAAAAAAAAEAAAAsA"
        "AAAYXVkdGEAAABZbWV0YQAAAAAAAAAhaGRscgAAAAAAAAAAbWRpcmFwcGwAAAAAAAAAAAAAAAAsaWxzdAAAACSpdG9vAAAAHGRhd"
        "GEAAAABAAAAAExhdmY2MS43LjEwMA=="
    )


def test_upload_magic_bytes_inspection(client, auth_headers):
    """Ensures disguised executable payloads are rejected and valid video streams are accepted."""
    import io

    # 1. Reject executable disguised as MP4
    fake_exe = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00malicious binary content")
    res_fake = client.post(
        "/api/v1/reel-intelligence/jobs/upload",
        files={"file": ("malicious.mp4", fake_exe, "video/mp4")},
        headers=auth_headers
    )
    assert res_fake.status_code == 422
    assert "signature does not match" in res_fake.json()["detail"]

    # 2. Reject unsupported MIME type
    text_file = io.BytesIO(b"simple text content")
    res_mime = client.post(
        "/api/v1/reel-intelligence/jobs/upload",
        files={"file": ("text.txt", text_file, "text/plain")},
        headers=auth_headers
    )
    assert res_mime.status_code == 400

    # 3. Accept valid MP4 container (fully formed with ftyp, moov, and mdat atoms)
    valid_video_bytes = generate_minimal_mp4_bytes()
    valid_video = io.BytesIO(valid_video_bytes)
    res_valid = client.post(
        "/api/v1/reel-intelligence/jobs/upload",
        files={"file": ("good_reel.mp4", valid_video, "video/mp4")},
        headers=auth_headers
    )
    assert res_valid.status_code == 202
    assert res_valid.json()["analysis_mode"] == "VIDEO_UPLOAD"
    upload_job_id = res_valid.json()["id"]

    # Poll status -> TestClient executes BackgroundTasks before return, so status is COMPLETED
    poll = client.get(f"/api/v1/reel-intelligence/jobs/{upload_job_id}", headers=auth_headers)
    assert poll.status_code == 200
    assert poll.json()["status"] == "COMPLETED", f"Job failed: {poll.json().get('error_message')}"
    upload_report_id = poll.json()["report_id"]
    assert upload_report_id is not None

    # Fetch persisted report
    rep = client.get(f"/api/v1/reel-intelligence/reports/{upload_report_id}", headers=auth_headers)
    assert rep.status_code == 200
    assert rep.json()["analysis_mode"] == "VIDEO_UPLOAD"
    assert "scores" in rep.json()


def test_rejected_upload_does_not_consume_ai_quota(client, auth_headers, db_session, test_creator_user):
    """
    Regression test: ensures uploads rejected for invalid magic bytes or invalid MIME
    do not decrement or consume the workspace's monthly AI analysis quota.
    """
    import io
    from app.services.subscription_service import get_workspace_subscription

    _, ws = test_creator_user
    sub = get_workspace_subscription(db_session, ws.id)
    initial_used = sub.ai_used_monthly

    # 1. Reject disguised executable
    fake_exe = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00malicious binary content")
    res1 = client.post(
        "/api/v1/reel-intelligence/jobs/upload",
        files={"file": ("malicious.mp4", fake_exe, "video/mp4")},
        headers=auth_headers
    )
    assert res1.status_code == 422
    db_session.refresh(sub)
    assert sub.ai_used_monthly == initial_used, "Malicious upload rejection must not consume AI quota"

    # 2. Reject unsupported MIME type
    text_file = io.BytesIO(b"simple text content")
    res2 = client.post(
        "/api/v1/reel-intelligence/jobs/upload",
        files={"file": ("doc.txt", text_file, "text/plain")},
        headers=auth_headers
    )
    assert res2.status_code == 400
    db_session.refresh(sub)
    assert sub.ai_used_monthly == initial_used, "Invalid MIME upload rejection must not consume AI quota"


def test_oversized_upload_refunds_quota_and_removes_file(client, auth_headers, db_session, test_creator_user, monkeypatch):
    """
    Regression test: ensures an upload exceeding MAX_VIDEO_SIZE_BYTES:
    1. Returns HTTP 413 Payload Too Large.
    2. Refunds exactly one quota unit (net change zero).
    3. Removes the temporary file from media_storage.
    4. Leaves no orphaned ReelMediaAsset or ReelAnalysisJob records.
    """
    import io
    import os
    import app.services.reel_intelligence_service as ris
    from app.services.subscription_service import get_workspace_subscription
    from app.models.reel_intelligence import ReelMediaAsset, ReelAnalysisJob

    _, ws = test_creator_user
    sub = get_workspace_subscription(db_session, ws.id)
    initial_used = sub.ai_used_monthly

    # Temporarily set MAX_VIDEO_SIZE_BYTES to 1500 bytes for deterministic testing
    monkeypatch.setattr(ris, "MAX_VIDEO_SIZE_BYTES", 1500)

    # Valid MP4 header (64 bytes) + padding to exceed 1500 bytes
    valid_header = generate_minimal_mp4_bytes()[:64]
    oversized_data = valid_header + b"\x00" * 3000
    oversized_file = io.BytesIO(oversized_data)

    res = client.post(
        "/api/v1/reel-intelligence/jobs/upload",
        files={"file": ("oversized_test.mp4", oversized_file, "video/mp4")},
        headers=auth_headers
    )
    assert res.status_code == 413
    assert "exceeds maximum allowed size" in res.json()["detail"].lower()

    # 1. Verify quota was refunded
    db_session.refresh(sub)
    assert sub.ai_used_monthly == initial_used, "Oversized upload must refund the allocated quota unit"

    # 2. Verify temporary file was deleted from disk
    ws_dir = os.path.join(ris.STORAGE_BASE_DIR, ws.id)
    if os.path.exists(ws_dir):
        files = [f for f in os.listdir(ws_dir) if "oversized_test" in f]
        assert len(files) == 0, f"Temporary file was not removed: {files}"

    # 3. Verify no orphaned database records
    assets = db_session.query(ReelMediaAsset).filter(ReelMediaAsset.workspace_id == ws.id).all()
    assert len(assets) == 0, "No ReelMediaAsset record should exist for rejected oversized file"
    jobs = db_session.query(ReelAnalysisJob).filter(ReelAnalysisJob.workspace_id == ws.id).all()
    assert len(jobs) == 0, "No ReelAnalysisJob should exist for rejected oversized file"


def test_streaming_exception_refunds_quota_and_cleans_file(client, auth_headers, db_session, test_creator_user, monkeypatch):
    """
    Regression test: ensures unexpected streaming exceptions (network disconnect mid-stream):
    1. Propagate safely to the caller.
    2. Refund the allocated quota unit.
    3. Remove any partially written temporary file from media_storage.
    4. Leave no orphaned database records.
    """
    import io
    import os
    import tempfile
    import app.services.reel_intelligence_service as ris
    from app.services.subscription_service import get_workspace_subscription
    from app.models.reel_intelligence import ReelMediaAsset, ReelAnalysisJob

    _, ws = test_creator_user
    sub = get_workspace_subscription(db_session, ws.id)
    initial_used = sub.ai_used_monthly

    valid_video = io.BytesIO(generate_minimal_mp4_bytes() + b"\x00" * 2048)

    orig_read = tempfile.SpooledTemporaryFile.read
    def faulty_read(self, *args, **kwargs):
        if len(args) > 0 and args[0] == 1024 * 1024:
            raise IOError("Simulated network disconnect during chunk streaming")
        return orig_read(self, *args, **kwargs)

    monkeypatch.setattr(tempfile.SpooledTemporaryFile, "read", faulty_read)

    with pytest.raises(IOError, match="Simulated network disconnect"):
        client.post(
            "/api/v1/reel-intelligence/jobs/upload",
            files={"file": ("stream_fault_test.mp4", valid_video, "video/mp4")},
            headers=auth_headers
        )

    # 1. Verify quota was refunded
    db_session.refresh(sub)
    assert sub.ai_used_monthly == initial_used, "Streaming exception must refund the allocated quota unit"

    # 2. Verify temporary file was deleted from disk
    ws_dir = os.path.join(ris.STORAGE_BASE_DIR, ws.id)
    if os.path.exists(ws_dir):
        files = [f for f in os.listdir(ws_dir) if "stream_fault_test" in f]
        assert len(files) == 0, f"Partial temporary file was not removed: {files}"

    # 3. Verify no orphaned database records
    assets = db_session.query(ReelMediaAsset).filter(ReelMediaAsset.workspace_id == ws.id).all()
    assert len(assets) == 0, "No ReelMediaAsset record should exist after streaming failure"
    jobs = db_session.query(ReelAnalysisJob).filter(ReelAnalysisJob.workspace_id == ws.id).all()
    assert len(jobs) == 0, "No ReelAnalysisJob should exist after streaming failure"


def test_db_commit_failure_during_job_creation_refunds_quota_and_cleans_file(client, auth_headers, db_session, test_creator_user, monkeypatch):
    """
    Regression test: ensures database failure during asset/job persistence:
    1. Propagates the database exception.
    2. Refunds the allocated quota unit via compensation.
    3. Removes the written temporary file from media_storage.
    4. Leaves no orphaned media assets or jobs in the database.
    """
    import io
    import os
    from sqlalchemy.exc import SQLAlchemyError
    import app.services.reel_intelligence_service as ris
    from app.services.subscription_service import get_workspace_subscription
    from app.models.reel_intelligence import ReelMediaAsset, ReelAnalysisJob

    _, ws = test_creator_user
    sub = get_workspace_subscription(db_session, ws.id)
    initial_used = sub.ai_used_monthly

    valid_video = io.BytesIO(generate_minimal_mp4_bytes())

    orig_flush = db_session.flush
    def faulty_flush(*args, **kwargs):
        raise SQLAlchemyError("Simulated database constraint or connection failure on flush")

    monkeypatch.setattr(db_session, "flush", faulty_flush)

    with pytest.raises(SQLAlchemyError, match="Simulated database constraint"):
        client.post(
            "/api/v1/reel-intelligence/jobs/upload",
            files={"file": ("db_fault_test.mp4", valid_video, "video/mp4")},
            headers=auth_headers
        )

    # Restore flush so test assertions can query the database
    monkeypatch.setattr(db_session, "flush", orig_flush)

    # 1. Verify quota was refunded
    db_session.refresh(sub)
    assert sub.ai_used_monthly == initial_used, "Database failure must refund the allocated quota unit"

    # 2. Verify temporary file was deleted from disk
    ws_dir = os.path.join(ris.STORAGE_BASE_DIR, ws.id)
    if os.path.exists(ws_dir):
        files = [f for f in os.listdir(ws_dir) if "db_fault_test" in f]
        assert len(files) == 0, f"Temporary file was not removed after DB failure: {files}"

    # 3. Verify no orphaned database records
    assets = db_session.query(ReelMediaAsset).filter(ReelMediaAsset.workspace_id == ws.id).all()
    assert len(assets) == 0, "No ReelMediaAsset should exist after DB failure"
    jobs = db_session.query(ReelAnalysisJob).filter(ReelAnalysisJob.workspace_id == ws.id).all()
    assert len(jobs) == 0, "No ReelAnalysisJob should exist after DB failure"



def test_idempotent_job_submission(client, auth_headers):
    """Submitting the exact same URL while a job is active returns the existing job."""
    test_url = "https://www.instagram.com/reel/CIdempotent123/"
    
    res1 = client.post("/api/v1/reel-intelligence/jobs/url", json={"url": test_url}, headers=auth_headers)
    assert res1.status_code == 202
    job1_id = res1.json()["id"]

    res2 = client.post("/api/v1/reel-intelligence/jobs/url", json={"url": test_url}, headers=auth_headers)
    assert res2.status_code == 202
    job2_id = res2.json()["id"]

    # Returns the same job ID
    assert job1_id == job2_id


def test_quota_exhaustion_enforcement(client, auth_headers, db_session, test_creator_user):
    """Verifies that exceeding monthly AI quota blocks new analysis submissions with 429."""
    from app.services.subscription_service import get_workspace_subscription

    _, workspace = test_creator_user
    sub = get_workspace_subscription(db_session, workspace.id)
    # Simulate full consumption of monthly quota
    sub.ai_used_monthly = sub.ai_limit_monthly
    db_session.commit()

    res = client.post(
        "/api/v1/reel-intelligence/jobs/url",
        json={"url": "https://www.instagram.com/reel/CQuotaExceeded/"},
        headers=auth_headers
    )
    assert res.status_code == 429
    assert "quota exceeded" in res.json()["detail"].lower()

    # Reset quota so subsequent tests pass cleanly
    sub.ai_used_monthly = 0
    db_session.commit()


def test_job_retry_rules(client, auth_headers):
    """Verifies that completed jobs cannot be retried, but failed jobs can."""
    # Create and run a connected reel job to completion
    res = client.post(
        "/api/v1/reel-intelligence/jobs/connected",
        json={"media_id": "ig_reel_ig_test_user_id_103"},
        headers=auth_headers
    )
    job_id = res.json()["id"]

    # Poll status (TestClient completes background tasks synchronously)
    poll = client.get(f"/api/v1/reel-intelligence/jobs/{job_id}", headers=auth_headers)
    assert poll.json()["status"] == "COMPLETED"

    # Attempting to retry completed job returns 400
    retry_res = client.post(f"/api/v1/reel-intelligence/jobs/{job_id}/retry", headers=auth_headers)
    assert retry_res.status_code == 400
    assert "Cannot retry" in retry_res.json()["detail"]


def test_report_history_listing_and_filtering(client, auth_headers):
    """Verifies searching and filtering analysis history."""
    res = client.get("/api/v1/reel-intelligence/reports?limit=10", headers=auth_headers)
    assert res.status_code == 200
    reports = res.json()
    assert isinstance(reports, list)
    if len(reports) > 0:
        first_title = reports[0]["title"]
        # Search filter
        search_res = client.get(f"/api/v1/reel-intelligence/reports?search={first_title[:4]}", headers=auth_headers)
        assert search_res.status_code == 200
        assert len(search_res.json()) >= 1


def test_comparison_security_and_validation(client, auth_headers, db_session, test_creator_user):
    """Verifies bounds (2-5), duplicate detection, missing IDs, and cross-workspace isolation for comparisons."""
    # Create two valid reports for the current workspace
    j1 = client.post("/api/v1/reel-intelligence/jobs/connected", json={"media_id": "sandbox_media_ig_test_user_id_1"}, headers=auth_headers)
    j2 = client.post("/api/v1/reel-intelligence/jobs/connected", json={"media_id": "sandbox_media_ig_test_user_id_2"}, headers=auth_headers)
    r1_id = client.get(f"/api/v1/reel-intelligence/jobs/{j1.json()['id']}", headers=auth_headers).json()["report_id"]
    r2_id = client.get(f"/api/v1/reel-intelligence/jobs/{j2.json()['id']}", headers=auth_headers).json()["report_id"]

    # 1. Less than 2 items -> 422 Unprocessable Entity (Pydantic schema validation)
    res_too_few = client.post("/api/v1/reel-intelligence/compare", json={"report_ids": [r1_id]}, headers=auth_headers)
    assert res_too_few.status_code == 422

    # 2. More than 5 items -> 422 Unprocessable Entity
    res_too_many = client.post(
        "/api/v1/reel-intelligence/compare",
        json={"report_ids": [r1_id, r2_id, "id3", "id4", "id5", "id6"]},
        headers=auth_headers
    )
    assert res_too_many.status_code == 422

    # 3. Duplicate IDs in request -> 400 Bad Request
    res_dup = client.post(
        "/api/v1/reel-intelligence/compare",
        json={"report_ids": [r1_id, r1_id]},
        headers=auth_headers
    )
    assert res_dup.status_code == 400
    assert "duplicate" in res_dup.json()["detail"].lower()

    # 4. Non-existent report ID -> 404 Not Found
    res_missing = client.post(
        "/api/v1/reel-intelligence/compare",
        json={"report_ids": [r1_id, "non_existent_rep_uuid"]},
        headers=auth_headers
    )
    assert res_missing.status_code == 404
    assert "not found" in res_missing.json()["detail"].lower()

    # 5. Cross-tenant attempt: Other user tries to compare with Creator's report
    other_user = User(
        email="tenant_comp_sec@other.io",
        hashed_password=get_password_hash("OtherPass123!"),
        full_name="Other Comp User",
        role="CREATOR"
    )
    db_session.add(other_user)
    db_session.flush()
    other_ws = Workspace(name="Other Workspace Comp", owner_id=other_user.id)
    db_session.add(other_ws)
    db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=other_ws.id, user_id=other_user.id, role_in_workspace="OWNER"))
    db_session.commit()

    other_token = create_access_token(data={"sub": other_user.id, "role": other_user.role, "workspace_id": other_ws.id})
    other_headers = {"Authorization": f"Bearer {other_token}"}

    # Other tenant creates 1 valid report in their own workspace
    other_j = client.post(
        "/api/v1/reel-intelligence/jobs/url",
        json={"url": "https://www.instagram.com/reel/COtherTenantSec1/"},
        headers=other_headers
    )
    assert other_j.status_code == 202
    other_r_id = client.get(f"/api/v1/reel-intelligence/jobs/{other_j.json()['id']}", headers=other_headers).json()["report_id"]

    # Other tenant attempts to compare their report with Creator's r1_id -> 404 Not Found (Cross-tenant protected!)
    cross_res = client.post(
        "/api/v1/reel-intelligence/compare",
        json={"report_ids": [other_r_id, r1_id]},
        headers=other_headers
    )
    assert cross_res.status_code == 404
    assert "not found" in cross_res.json()["detail"].lower()


def test_ssrf_advanced_dns_and_metadata_blocking(client, auth_headers):
    """Verifies that cloud metadata hostnames, nip.io private mappings, and IPv6 loopback are blocked."""
    blocked_urls = [
        "http://metadata.google.internal/computeMetadata/v1/video.mp4",
        "http://instance-data/latest/meta-data/reel.mp4",
        "http://127.0.0.1.nip.io/exploit.mp4",
        "http://[::1]/internal.mp4"
    ]
    for b_url in blocked_urls:
        res = client.post("/api/v1/reel-intelligence/jobs/url", json={"url": b_url}, headers=auth_headers)
        assert res.status_code == 422, f"Expected 422 for blocked URL '{b_url}', got {res.status_code}: {res.text}"


def _sample_report_fields(title: str = "Initial Report", score: float = 72.5) -> dict:
    return {
        "title": title,
        "analysis_mode": "PUBLIC_URL",
        "thumbnail_url": "https://example.com/thumb.jpg",
        "duration_seconds": 18.0,
        "creative_quality_score": score,
        "performance_score": score,
        "growth_conversion_score": score,
        "viral_potential_estimate": score,
        "score_breakdown_json": "{}",
        "calculated_metrics_json": "{}",
        "video_intelligence_json": "{}",
        "timeline_findings_json": "[]",
        "prioritized_action_plan_json": "[]",
        "creative_alternatives_json": "{}",
        "provenance_json": "{}",
    }


def test_first_report_and_repeated_completed_job_reuses_report(client, auth_headers, db_session, test_creator_user, monkeypatch):
    """
    Verifies:
    1. First submission creates exactly one ReelReport and marks the job COMPLETED with report_id.
    2. Repeated URL submission and direct execute_reel_analysis() on a COMPLETED job reuse the
       existing report without invoking the pipeline again or violating reel_reports_job_id_key.
    """
    import app.services.reel_intelligence_service as ris

    _, workspace = test_creator_user
    url = "https://www.instagram.com/reel/CReuseUnique1/"

    first_res = client.post("/api/v1/reel-intelligence/jobs/url", json={"url": url}, headers=auth_headers)
    assert first_res.status_code == 202
    job_id = first_res.json()["id"]

    poll1 = client.get(f"/api/v1/reel-intelligence/jobs/{job_id}", headers=auth_headers)
    assert poll1.status_code == 200
    assert poll1.json()["status"] == "COMPLETED"
    report_id = poll1.json()["report_id"]
    assert report_id is not None

    reports = db_session.query(ReelReport).filter(ReelReport.job_id == job_id).all()
    assert len(reports) == 1
    assert reports[0].id == report_id

    # Re-submitting the same URL must reuse the completed job/report without re-running analysis
    pipeline_calls = {"count": 0}

    def fail_if_reprocessed(*args, **kwargs):
        pipeline_calls["count"] += 1
        raise AssertionError("Completed job should reuse its existing report instead of re-processing")

    monkeypatch.setattr(ris, "run_video_intelligence_pipeline", fail_if_reprocessed)

    second_res = client.post("/api/v1/reel-intelligence/jobs/url", json={"url": url}, headers=auth_headers)
    assert second_res.status_code == 202
    assert second_res.json()["id"] == job_id
    assert second_res.json()["status"] == "COMPLETED"
    assert second_res.json()["report_id"] == report_id

    # Polling after repeat submission confirms status stays COMPLETED and report count stays 1
    poll2 = client.get(f"/api/v1/reel-intelligence/jobs/{job_id}", headers=auth_headers)
    assert poll2.status_code == 200
    assert poll2.json()["status"] == "COMPLETED"
    assert poll2.json()["report_id"] == report_id
    assert poll2.json()["error_message"] is None

    # Direct execute_reel_analysis on COMPLETED job also reuses existing report cleanly
    reused_report = ris.execute_reel_analysis(db_session, job_id, workspace_id=workspace.id)
    assert reused_report.id == report_id
    assert pipeline_calls["count"] == 0
    assert db_session.query(ReelReport).filter(ReelReport.job_id == job_id).count() == 1


def test_retry_after_failure_updates_existing_report_without_duplicate(client, auth_headers, db_session, test_creator_user, monkeypatch):
    """
    Simulates a job whose ReelReport already exists in the DB (e.g. failed before job finalization
    or corrupted by prior state) and verifies retrying updates that report rather than inserting a duplicate.
    """
    import app.services.reel_intelligence_service as ris

    _, workspace = test_creator_user
    create_res = client.post(
        "/api/v1/reel-intelligence/jobs/connected",
        json={"media_id": "ig_reel_ig_test_user_id_102"},
        headers=auth_headers,
    )
    assert create_res.status_code == 202
    job_id = create_res.json()["id"]

    job = db_session.query(ReelAnalysisJob).filter(ReelAnalysisJob.id == job_id).first()
    existing_report = db_session.query(ReelReport).filter(ReelReport.job_id == job_id).first()
    assert existing_report is not None
    original_report_id = existing_report.id

    # Mark existing report stale and put job in FAILED state (simulating failure after report persistence)
    existing_report.title = "Stale Partial Report"
    existing_report.creative_quality_score = 12.0
    job.status = "FAILED"
    job.error_message = "Transient downstream interruption"
    job.report_id = None
    db_session.commit()

    # Retry via API
    retry_res = client.post(f"/api/v1/reel-intelligence/jobs/{job_id}/retry", headers=auth_headers)
    assert retry_res.status_code == 200

    poll = client.get(f"/api/v1/reel-intelligence/jobs/{job_id}", headers=auth_headers)
    assert poll.status_code == 200
    assert poll.json()["status"] == "COMPLETED"
    assert poll.json()["report_id"] == original_report_id
    assert poll.json()["error_message"] is None

    all_reports = db_session.query(ReelReport).filter(
        ReelReport.job_id == job_id,
        ReelReport.workspace_id == workspace.id,
    ).all()
    assert len(all_reports) == 1
    assert all_reports[0].id == original_report_id
    assert all_reports[0].title != "Stale Partial Report"
    assert all_reports[0].creative_quality_score != 12.0

    # Also verify direct upsert_reel_report_for_job updates in place when called directly
    updated = ris.upsert_reel_report_for_job(
        db_session,
        job,
        _sample_report_fields(title="Explicitly Refreshed Title", score=91.0),
        workspace_id=workspace.id,
    )
    assert updated.id == original_report_id
    assert updated.title == "Explicitly Refreshed Title"
    assert updated.creative_quality_score == 91.0
    assert db_session.query(ReelReport).filter(ReelReport.job_id == job_id).count() == 1


def test_concurrent_unique_violation_recovery_and_multithread_persistence(tmp_path, db_session, test_creator_user, monkeypatch):
    """
    Tests:
    1. PostgreSQL-style IntegrityError (pgcode 23505 on reel_reports_job_id_key) raised inside
       SAVEPOINT when check-then-insert races with another worker recovers cleanly and updates
       the single report instead of failing.
    2. Real concurrent multi-threaded sessions persisting for the same job_id produce 1 report.
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy import create_engine
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import sessionmaker
    import app.services.reel_intelligence_service as ris
    from app.database import Base

    user, workspace = test_creator_user

    # Part A: Simulate check-then-insert race hitting PostgreSQL UniqueViolation (pgcode 23505)
    job = ReelAnalysisJob(
        workspace_id=workspace.id,
        analysis_mode="PUBLIC_URL",
        input_type="url",
        status="GENERATING_AI_REPORT",
        source_url="https://www.instagram.com/reel/CRaceTest1/",
    )
    db_session.add(job)
    db_session.flush()
    preexisting = ReelReport(
        workspace_id=workspace.id,
        job_id=job.id,
        **_sample_report_fields(title="Winning Worker Report", score=70.0),
    )
    db_session.add(preexisting)
    db_session.commit()
    winning_id = preexisting.id

    orig_lookup = ris.get_job_report_for_workspace
    lookup_state = {"calls": 0}

    def stale_first_lookup(db, j_id, ws_id, for_update=False):
        lookup_state["calls"] += 1
        # Simulate another worker inserting between Worker B's initial check and INSERT
        if lookup_state["calls"] == 1:
            return None
        return orig_lookup(db, j_id, ws_id, for_update=for_update)

    monkeypatch.setattr(ris, "get_job_report_for_workspace", stale_first_lookup)

    class _FakePgDiag:
        constraint_name = "reel_reports_job_id_key"

    class _FakePgOrig(Exception):
        pgcode = "23505"
        diag = _FakePgDiag()

    orig_flush = db_session.flush
    flush_state = {"injected": False}

    def pg_unique_conflict_once(*args, **kwargs):
        if not flush_state["injected"]:
            flush_state["injected"] = True
            raise IntegrityError(
                "INSERT INTO reel_reports (...) VALUES (...)",
                {},
                _FakePgOrig('duplicate key value violates unique constraint "reel_reports_job_id_key"'),
            )
        return orig_flush(*args, **kwargs)

    monkeypatch.setattr(db_session, "flush", pg_unique_conflict_once)

    recovered = ris.upsert_reel_report_for_job(
        db_session,
        job,
        _sample_report_fields(title="Racing Worker Updated Report", score=88.5),
        workspace_id=workspace.id,
    )
    monkeypatch.setattr(ris, "get_job_report_for_workspace", orig_lookup)
    monkeypatch.setattr(db_session, "flush", orig_flush)

    assert recovered.id == winning_id
    assert recovered.title == "Racing Worker Updated Report"
    assert recovered.creative_quality_score == 88.5
    db_session.refresh(job)
    assert job.status == "COMPLETED"
    assert job.report_id == winning_id
    assert db_session.query(ReelReport).filter(ReelReport.job_id == job.id).count() == 1

    # Part B: Real two-thread concurrent sessions against isolated file-backed SQLite DB
    db_file = tmp_path / "concurrent_reports.db"
    conc_engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(bind=conc_engine)
    ConcSession = sessionmaker(autocommit=False, autoflush=False, bind=conc_engine)

    seed_db = ConcSession()
    seed_user = User(id="conc_u1", email="conc@woka.io", hashed_password=get_password_hash("Pass123!"), full_name="Conc User", role="CREATOR")
    seed_ws = Workspace(id="conc_w1", name="Conc WS", owner_id="conc_u1")
    seed_job = ReelAnalysisJob(
        id="conc_job_1",
        workspace_id="conc_w1",
        analysis_mode="PUBLIC_URL",
        input_type="url",
        status="GENERATING_AI_REPORT",
        source_url="https://www.instagram.com/reel/CConcurrent1/",
    )
    seed_db.add_all([seed_user, seed_ws, seed_job])
    seed_db.commit()
    seed_db.close()

    barrier = threading.Barrier(2)

    def run_worker(worker_idx: int) -> str:
        w_db = ConcSession()
        try:
            w_job = w_db.query(ReelAnalysisJob).filter(ReelAnalysisJob.id == "conc_job_1").first()
            barrier.wait(timeout=5)
            rep = ris.upsert_reel_report_for_job(
                w_db,
                w_job,
                _sample_report_fields(title=f"Worker {worker_idx} Report", score=80.0 + worker_idx),
                workspace_id="conc_w1",
            )
            return rep.id
        finally:
            w_db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(run_worker, 1)
        f2 = pool.submit(run_worker, 2)
        id1 = f1.result(timeout=15)
        id2 = f2.result(timeout=15)

    assert id1 == id2
    verify_db = ConcSession()
    try:
        rows = verify_db.query(ReelReport).filter(ReelReport.job_id == "conc_job_1").all()
        final_job = verify_db.query(ReelAnalysisJob).filter(ReelAnalysisJob.id == "conc_job_1").first()
        assert len(rows) == 1
        assert final_job.status == "COMPLETED"
        assert final_job.report_id == rows[0].id
    finally:
        verify_db.close()
        conc_engine.dispose()


def test_cross_workspace_report_and_job_rejection(client, db_session, test_creator_user):
    """Ensures cross-workspace access, retry, and report upsert/execution are strictly rejected."""
    import app.services.reel_intelligence_service as ris

    _, ws_a = test_creator_user

    user_b = User(
        email="cross_ws_b@other.io",
        hashed_password=get_password_hash("OtherPass123!"),
        full_name="User B",
        role="CREATOR",
    )
    db_session.add(user_b)
    db_session.flush()
    ws_b = Workspace(name="Workspace B", owner_id=user_b.id)
    db_session.add(ws_b)
    db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=ws_b.id, user_id=user_b.id, role_in_workspace="OWNER"))
    db_session.commit()

    headers_a = {"Authorization": f"Bearer {create_access_token({'sub': test_creator_user[0].id, 'role': 'CREATOR', 'workspace_id': ws_a.id})}"}
    headers_b = {"Authorization": f"Bearer {create_access_token({'sub': user_b.id, 'role': 'CREATOR', 'workspace_id': ws_b.id})}"}

    submit_a = client.post(
        "/api/v1/reel-intelligence/jobs/url",
        json={"url": "https://www.instagram.com/reel/CCrossTenantGuard/"},
        headers=headers_a,
    )
    assert submit_a.status_code == 202
    job_a_id = submit_a.json()["id"]
    job_a_detail = client.get(f"/api/v1/reel-intelligence/jobs/{job_a_id}", headers=headers_a).json()
    report_a_id = job_a_detail["report_id"]

    # Workspace B cannot view, retry, or fetch Workspace A's job/report
    assert client.get(f"/api/v1/reel-intelligence/jobs/{job_a_id}", headers=headers_b).status_code == 404
    assert client.post(f"/api/v1/reel-intelligence/jobs/{job_a_id}/retry", headers=headers_b).status_code == 404
    assert client.get(f"/api/v1/reel-intelligence/reports/{report_a_id}", headers=headers_b).status_code == 404

    # Service-layer calls with mismatched workspace_id must fail loudly and leave report untouched
    job_a = db_session.query(ReelAnalysisJob).filter(ReelAnalysisJob.id == job_a_id).first()
    with pytest.raises(PermissionError):
        ris.execute_reel_analysis(db_session, job_a_id, workspace_id=ws_b.id)

    with pytest.raises(PermissionError):
        ris.upsert_reel_report_for_job(
            db_session,
            job_a,
            _sample_report_fields(title="Cross Tenant Overwrite Attempt", score=1.0),
            workspace_id=ws_b.id,
        )

    unchanged = db_session.query(ReelReport).filter(ReelReport.id == report_a_id).first()
    assert unchanged.workspace_id == ws_a.id
    assert unchanged.title != "Cross Tenant Overwrite Attempt"


def test_raw_sql_exception_sanitized_in_job_error_and_logged(client, auth_headers, db_session, monkeypatch, caplog):
    """
    Ensures internal SQL/database exceptions during pipeline failure are logged with diagnostics
    on the backend while returning a user-friendly message in job.error_message (no SQL leaks).
    """
    import logging
    from sqlalchemy.exc import IntegrityError
    import app.services.reel_intelligence_service as ris

    def failing_upsert(*args, **kwargs):
        raise IntegrityError(
            "INSERT INTO reel_reports (id, workspace_id, job_id) VALUES (%s, %s, %s)",
            {},
            Exception('psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint "reel_reports_job_id_key"'),
        )

    monkeypatch.setattr(ris, "upsert_reel_report_for_job", failing_upsert)

    with caplog.at_level(logging.ERROR):
        res = client.post(
            "/api/v1/reel-intelligence/jobs/url",
            json={"url": "https://www.instagram.com/reel/CSanitizeError1/"},
            headers=auth_headers,
        )
    assert res.status_code == 202
    job_id = res.json()["id"]

    poll = client.get(f"/api/v1/reel-intelligence/jobs/{job_id}", headers=auth_headers)
    assert poll.status_code == 200
    body = poll.json()
    assert body["status"] == "FAILED"
    assert body["error_message"]
    lower_err = body["error_message"].lower()
    assert "psycopg2" not in lower_err
    assert "reel_reports_job_id_key" not in lower_err
    assert "insert into" not in lower_err
    assert "[sql:" not in lower_err
    assert "retry analysis" in lower_err
    assert any("Reel analysis pipeline failed" in rec.message for rec in caplog.records)


def test_missing_metrics_never_fabricated_and_retention_unclaimed(
    client, auth_headers, test_creator_user, db_session, monkeypatch
):
    """
    Ensures missing public/connected metrics remain None with category=UNAVAILABLE,
    retention is never claimed measured without timestamped retention telemetry,
    un-decoded streams do not fabricate duration/FPS/audio, and generic placeholder thumbnails are never used.
    """
    from app.models.instagram import InstagramAccount
    import app.services.instagram_service as ig_svc

    # Case A: Public URL submitted with no creator-declared metrics
    url_res = client.post(
        "/api/v1/reel-intelligence/jobs/url",
        json={"url": "https://www.instagram.com/reel/C_missing_metrics_test/"},
        headers=auth_headers,
    )
    assert url_res.status_code == 202
    url_job = client.get(f"/api/v1/reel-intelligence/jobs/{url_res.json()['id']}", headers=auth_headers).json()
    assert url_job["status"] == "COMPLETED"

    url_report = client.get(
        f"/api/v1/reel-intelligence/reports/{url_job['report_id']}",
        headers=auth_headers,
    ).json()

    for key in ["views", "likes", "comments", "shares", "saves", "reach", "engagement_rate", "watch_ratio"]:
        metric = url_report["calculated_metrics"][key]
        assert metric["value"] is None, f"Expected {key} to be None, got {metric['value']}"
        assert metric["category"] == "UNAVAILABLE"
        assert metric["is_simulated"] is False

    assert url_report["duration_seconds"] == 0.0
    assert url_report["thumbnail_url"] is None
    assert url_report["provenance"]["duration_measured"] is False
    assert url_report["provenance"]["fps_measured"] is False
    assert url_report["provenance"]["video_stream_analyzed"] is False
    assert url_report["provenance"]["audio_speech_analyzed"] is False
    assert url_report["provenance"]["caption_analyzed"] is False
    assert url_report["provenance"]["is_retention_measured"] is False
    assert url_report["scores"]["creative_quality"]["data_available"] is False
    assert url_report["scores"]["performance"]["data_available"] is False
    assert url_report["scores"]["performance"]["rating"] == "UNAVAILABLE"
    assert url_report["scores"]["growth_conversion"]["data_available"] is False
    assert url_report["scores"]["growth_conversion"]["rating"] == "UNAVAILABLE"
    assert url_report["scores"]["viral_potential"]["data_available"] is False
    assert url_report["scores"]["growth_conversion"]["rating"] == "UNAVAILABLE"

    # Case B: Live connected Reel where Meta omits views, like_count, comments_count, avg_watch_time, and thumbnail_url
    _, ws = test_creator_user
    account = db_session.query(InstagramAccount).filter(InstagramAccount.workspace_id == ws.id).first()
    account.is_sandbox = False
    db_session.commit()

    partial_media = {
        "id": "ig_live_partial_1",
        "media_type": "VIDEO",
        "media_product_type": "REELS",
        "caption": "Budget meal prep grocery list for busy weeknights",
        "permalink": "https://www.instagram.com/reel/C_partial_1/",
    }
    monkeypatch.setattr(ig_svc, "fetch_instagram_media_by_id", lambda *args, **kwargs: dict(partial_media))
    monkeypatch.setattr(ig_svc, "fetch_instagram_media_list", lambda *args, **kwargs: [dict(partial_media)])
    monkeypatch.setattr(
        ig_svc,
        "fetch_media_insights",
        lambda *args, **kwargs: {"reach": 2500, "saved": 40, "shares": 15},
    )

    conn_res = client.post(
        "/api/v1/reel-intelligence/jobs/connected",
        json={"media_id": "ig_live_partial_1"},
        headers=auth_headers,
    )
    assert conn_res.status_code == 202
    conn_job = client.get(f"/api/v1/reel-intelligence/jobs/{conn_res.json()['id']}", headers=auth_headers).json()
    assert conn_job["status"] == "COMPLETED"

    conn_report = client.get(
        f"/api/v1/reel-intelligence/reports/{conn_job['report_id']}",
        headers=auth_headers,
    ).json()
    cm = conn_report["calculated_metrics"]
    assert cm["views"]["value"] is None and cm["views"]["category"] == "UNAVAILABLE"
    assert cm["likes"]["value"] is None and cm["likes"]["category"] == "UNAVAILABLE"
    assert cm["comments"]["value"] is None and cm["comments"]["category"] == "UNAVAILABLE"
    assert cm["watch_ratio"]["value"] is None and cm["watch_ratio"]["category"] == "UNAVAILABLE"
    assert cm["reach"]["value"] == 2500.0 and cm["reach"]["category"] == "MEASURED"
    assert cm["saves"]["value"] == 40.0 and cm["saves"]["category"] == "MEASURED"
    assert cm["shares"]["value"] == 15.0 and cm["shares"]["category"] == "MEASURED"
    assert conn_report["thumbnail_url"] is None
    assert conn_report["provenance"]["is_retention_measured"] is False
    assert conn_report["provenance"]["is_simulated"] is False

    # History summary also exposes missing counts honestly
    history = client.get("/api/v1/reel-intelligence/reports", headers=auth_headers).json()
    conn_summary = next(item for item in history if item["id"] == conn_report["id"])
    assert conn_summary["views_count"] is None
    assert conn_summary["likes_count"] is None
    assert conn_summary["duration_measured"] is False
    assert conn_summary["is_simulated"] is False


def test_sandbox_simulated_data_is_visibly_labeled_and_not_live_meta(client, auth_headers):
    """
    Verifies sandbox/demo connected Reels are explicitly flagged as simulated across
    /connected-reels, report metrics, provenance, and /reports summaries, and never use
    Meta Graph API labels or unsplash placeholder URLs.
    """
    reels_res = client.get("/api/v1/reel-intelligence/connected-reels", headers=auth_headers)
    assert reels_res.status_code == 200
    payload = reels_res.json()
    assert payload["has_connected_account"] is True
    assert payload["is_sandbox"] is True
    assert len(payload["reels"]) >= 1

    first_reel = payload["reels"][0]
    assert first_reel["is_simulated"] is True
    assert first_reel["data_source"] == "SANDBOX_SIMULATION"
    assert "unsplash.com" not in (first_reel.get("thumbnail_url") or "")

    job_res = client.post(
        "/api/v1/reel-intelligence/jobs/connected",
        json={
            "media_id": first_reel["media_id"],
            "title": first_reel["title"],
            "caption": first_reel["caption"],
        },
        headers=auth_headers,
    )
    assert job_res.status_code == 202
    job_body = client.get(f"/api/v1/reel-intelligence/jobs/{job_res.json()['id']}", headers=auth_headers).json()
    assert job_body["status"] == "COMPLETED"

    report = client.get(f"/api/v1/reel-intelligence/reports/{job_body['report_id']}", headers=auth_headers).json()
    assert report["provenance"]["is_simulated"] is True
    assert report["provenance"]["metric_source_mode"] == "SANDBOX_SIMULATION"
    assert any("sandbox" in lim.lower() or "simulated" in lim.lower() for lim in report["provenance"]["limitations"])

    for metric_key in ["views", "likes", "comments", "shares", "saves", "reach", "engagement_rate"]:
        metric = report["calculated_metrics"][metric_key]
        assert metric["category"] == "SIMULATED"
        assert metric["is_simulated"] is True
        assert "Sandbox Simulation" in metric["source"]
        assert not metric["source"].startswith("Meta Graph API")

    history = client.get("/api/v1/reel-intelligence/reports", headers=auth_headers).json()
    summary = next(item for item in history if item["id"] == report["id"])
    assert summary["is_simulated"] is True
    assert summary["metric_source"] == "SANDBOX_SIMULATION"


def test_uploaded_video_derives_real_opencv_frames_and_reel_specific_diagnosis(client, auth_headers, tmp_path):
    """
    Uploads a real OpenCV-encoded 9:16 video with a mid-video visual cut and verifies that
    duration, FPS, resolution, frame telemetry, cover thumbnail, timeline timestamps, and
    Reel-specific diagnosis originate from the real uploaded video without generic boilerplate.
    """
    import cv2
    import numpy as np

    video_path = tmp_path / "baking_sourdough_tips.mp4"
    width, height, fps = 540, 960, 10.0
    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    assert writer.isOpened(), "OpenCV VideoWriter failed to open mp4v file"

    try:
        for idx in range(30):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            if idx < 15:
                frame[:, :] = (35, 45, 165)
                cv2.rectangle(frame, (80, 320), (460, 620), (200, 220, 240), -1)
            else:
                frame[:, :] = (210, 200, 70)
                # Place high-contrast overlay rectangle in lower Instagram Reel UI zone
                cv2.rectangle(frame, (40, 760), (500, 910), (255, 255, 255), -1)
            writer.write(frame)
    finally:
        writer.release()

    with open(video_path, "rb") as fh:
        up_res = client.post(
            "/api/v1/reel-intelligence/jobs/upload",
            files={"file": ("baking_sourdough_tips.mp4", fh, "video/mp4")},
            headers=auth_headers,
        )
    assert up_res.status_code == 202
    job_body = client.get(f"/api/v1/reel-intelligence/jobs/{up_res.json()['id']}", headers=auth_headers).json()
    assert job_body["status"] == "COMPLETED"

    report = client.get(f"/api/v1/reel-intelligence/reports/{job_body['report_id']}", headers=auth_headers).json()
    vi_meta = report["video_intelligence"]["metadata"]
    vi_frames = report["video_intelligence"]["frame_telemetry"]

    assert 2.5 <= report["duration_seconds"] <= 3.5
    assert 9.0 <= vi_meta["fps"] <= 11.0
    assert vi_meta["resolution"] == "540x960"
    assert vi_meta["aspect_ratio"] == "9:16"
    assert vi_meta["video_stream_analyzed"] is True
    assert len(vi_frames["frame_observations"]) >= 3
    assert report["provenance"]["duration_measured"] is True
    assert report["provenance"]["fps_measured"] is True
    assert report["provenance"]["video_stream_analyzed"] is True
    assert report["provenance"]["audio_speech_analyzed"] is False

    # Cover frame thumbnail is real extracted JPEG and serves cleanly
    assert report["thumbnail_url"] and report["thumbnail_url"].startswith("/api/v1/reel-intelligence/thumbnails/")
    thumb_res = client.get(report["thumbnail_url"])
    assert thumb_res.status_code == 200
    assert thumb_res.headers["content-type"].startswith("image/jpeg")

    # Creative quality score is available from real frames, while post-publish metrics remain UNAVAILABLE
    assert report["scores"]["creative_quality"]["data_available"] is True
    assert report["scores"]["performance"]["data_available"] is False
    assert report["scores"]["growth_conversion"]["data_available"] is False
    assert report["calculated_metrics"]["views"]["category"] == "UNAVAILABLE"

    # Timeline findings must stay within the real ~3s duration (no fabricated 14s/45s timestamps)
    for finding in report["timeline_findings"]:
        assert finding["timestamp_end_seconds"] <= report["duration_seconds"] + 0.5
        assert finding["source"]
        assert finding["limitations"]

    # Creative output reflects actual video filename/topic instead of hardcoded generic prompts
    hook_texts = [h.get("hook_text", "") for h in report["creative_alternatives"].get("alternative_hooks", [])]
    caption_texts = [c.get("text", "") for c in report["creative_alternatives"].get("caption_suggestions", [])]
    action_texts = [
        f"{a.get('area', '')} {a.get('what_to_change', '')} {a.get('how_to_implement', '')}"
        for a in report["prioritized_action_plan"]
    ]
    combined_creative_text = " ".join(hook_texts + caption_texts + action_texts).lower()
    assert "baking" in combined_creative_text or "sourdough" in combined_creative_text
    assert "hidden instagram setting for 14 days" not in combined_creative_text
    assert "comment 'scale'" not in combined_creative_text


def test_source_mapping_accuracy_and_unsupported_claims_rejected(
    client, auth_headers, test_creator_user, db_session, monkeypatch
):
    """
    Verifies MEASURED vs CALCULATED vs UNAVAILABLE source mappings for a live connected Reel,
    preservation of genuine CDN thumbnails, rejection of unmeasured retention claims when only
    average watch time exists, and data-driven compare takeaways without canned multipliers.
    """
    from app.models.instagram import InstagramAccount
    import app.services.instagram_service as ig_svc

    _, ws = test_creator_user
    account = db_session.query(InstagramAccount).filter(InstagramAccount.workspace_id == ws.id).first()
    account.is_sandbox = False
    db_session.commit()

    media_catalog = {
        "ig_coffee_1": {
            "id": "ig_coffee_1",
            "media_type": "VIDEO",
            "media_product_type": "REELS",
            "caption": "Cold brew coffee extraction ratio for smooth mornings. Save this recipe!",
            "like_count": 320,
            "comments_count": 14,
            "thumbnail_url": "https://scontent.cdninstagram.com/coffee_thumb.jpg",
            "permalink": "https://www.instagram.com/reel/C_coffee_1/",
        },
        "ig_fitness_2": {
            "id": "ig_fitness_2",
            "media_type": "VIDEO",
            "media_product_type": "REELS",
            "caption": "Mobility warm-up routine for runners before race day.",
            "like_count": 90,
            "comments_count": 4,
            "thumbnail_url": "https://scontent.cdninstagram.com/fitness_thumb.jpg",
            "permalink": "https://www.instagram.com/reel/C_fitness_2/",
        },
    }
    insights_catalog = {
        "ig_coffee_1": {
            "views": 8000,
            "reach": 6400,
            "saved": 180,
            "shares": 45,
            "ig_reels_avg_watch_time": 11.0,
        },
        "ig_fitness_2": {
            "views": 2500,
            "reach": 2100,
            "saved": 30,
            "shares": 10,
        },
    }

    monkeypatch.setattr(
        ig_svc,
        "fetch_instagram_media_by_id",
        lambda *args, **kwargs: dict(media_catalog[kwargs.get("media_id") if "media_id" in kwargs else args[1]]),
    )
    monkeypatch.setattr(
        ig_svc,
        "fetch_instagram_media_list",
        lambda *args, **kwargs: [dict(m) for m in media_catalog.values()],
    )
    monkeypatch.setattr(
        ig_svc,
        "fetch_media_insights",
        lambda *args, **kwargs: dict(insights_catalog[kwargs.get("media_id") if "media_id" in kwargs else args[1]]),
    )

    report_ids = []
    for mid in ["ig_coffee_1", "ig_fitness_2"]:
        res = client.post(
            "/api/v1/reel-intelligence/jobs/connected",
            json={"media_id": mid},
            headers=auth_headers,
        )
        assert res.status_code == 202
        job = client.get(f"/api/v1/reel-intelligence/jobs/{res.json()['id']}", headers=auth_headers).json()
        assert job["status"] == "COMPLETED"
        report_ids.append(job["report_id"])

    coffee_report = client.get(
        f"/api/v1/reel-intelligence/reports/{report_ids[0]}",
        headers=auth_headers,
    ).json()

    assert coffee_report["thumbnail_url"] == "https://scontent.cdninstagram.com/coffee_thumb.jpg"
    cm = coffee_report["calculated_metrics"]
    assert cm["views"]["value"] == 8000.0 and cm["views"]["category"] == "MEASURED"
    assert cm["likes"]["value"] == 320.0 and cm["likes"]["category"] == "MEASURED"
    assert cm["comments"]["value"] == 14.0 and cm["comments"]["category"] == "MEASURED"
    assert cm["saves"]["value"] == 180.0 and cm["saves"]["category"] == "MEASURED"
    assert cm["shares"]["value"] == 45.0 and cm["shares"]["category"] == "MEASURED"
    assert cm["reach"]["value"] == 6400.0 and cm["reach"]["category"] == "MEASURED"
    assert cm["engagement_rate"]["category"] == "CALCULATED"
    assert cm["watch_ratio"]["category"] == "UNAVAILABLE"

    assert coffee_report["provenance"]["is_retention_measured"] is False
    assert coffee_report["provenance"]["video_stream_analyzed"] is False
    assert coffee_report["provenance"]["audio_speech_analyzed"] is False
    assert coffee_report["provenance"]["caption_analyzed"] is True

    coffee_text = " ".join(
        [h.get("hook_text", "") for h in coffee_report["creative_alternatives"].get("alternative_hooks", [])]
        + [c.get("text", "") for c in coffee_report["creative_alternatives"].get("caption_suggestions", [])]
    ).lower()
    assert "coffee" in coffee_text or "brew" in coffee_text or "extraction" in coffee_text
    assert "comment 'scale'" not in coffee_text

    # Compare the two reports and ensure comparison takeaways are grounded in real report numbers
    comp_res = client.post(
        "/api/v1/reel-intelligence/compare",
        json={"report_ids": report_ids},
        headers=auth_headers,
    )
    assert comp_res.status_code == 200
    comp_body = comp_res.json()
    assert comp_body["winner_id"] == report_ids[0]
    takeaways_joined = " ".join(comp_body["comparative_takeaways"])
    assert "3.4x higher comment density" not in takeaways_joined
    assert "8.73%" in takeaways_joined
    assert "engagement rate" in takeaways_joined.lower()



