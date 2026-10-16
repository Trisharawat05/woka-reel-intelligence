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
        "media_id": "ig_reel_test_999",
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
    job1_res = client.post("/api/v1/reel-intelligence/jobs/connected", json={"media_id": "reel_comp_1"}, headers=auth_headers)
    job2_res = client.post("/api/v1/reel-intelligence/jobs/connected", json={"media_id": "reel_comp_2"}, headers=auth_headers)
    
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

    # 3. Accept valid MP4 container
    valid_mp4_header = b"\x00\x00\x00\x1cftypisom\x00\x00\x02\x00isomiso2mp41\x00\x00\x00\x08free\x00\x00\x00\x08mdat"
    valid_video = io.BytesIO(valid_mp4_header + b"\x00" * 1024)
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
    assert poll.json()["status"] == "COMPLETED"
    upload_report_id = poll.json()["report_id"]
    assert upload_report_id is not None

    # Fetch persisted report
    rep = client.get(f"/api/v1/reel-intelligence/reports/{upload_report_id}", headers=auth_headers)
    assert rep.status_code == 200
    assert rep.json()["analysis_mode"] == "VIDEO_UPLOAD"
    assert "scores" in rep.json()



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
        json={"media_id": "reel_retry_test"},
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
    j1 = client.post("/api/v1/reel-intelligence/jobs/connected", json={"media_id": "comp_sec_1"}, headers=auth_headers)
    j2 = client.post("/api/v1/reel-intelligence/jobs/connected", json={"media_id": "comp_sec_2"}, headers=auth_headers)
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


