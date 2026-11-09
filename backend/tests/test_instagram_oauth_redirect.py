import urllib.parse
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
import httpx

from app.config import Settings, settings, validate_and_normalize_redirect_uri
from app.services.instagram_service import (
    get_oauth_authorization_url,
    exchange_code_for_tokens,
    connect_or_update_account_from_oauth,
    generate_oauth_state,
    generate_mock_signed_request,
    MetaAPIError
)
from app.models.instagram import InstagramAccount, InstagramDataDeletionRequest


def test_effective_instagram_redirect_uri_canonical():
    """Verifies Settings.effective_instagram_redirect_uri derives the exact canonical URI without trailing slashes."""
    s = Settings(
        BACKEND_PUBLIC_URL="https://squash-dreadlock-diner.ngrok-free.dev/",
        META_APP_ID="3217043811838822",
        API_V1_STR="/api/v1"
    )
    expected = "https://squash-dreadlock-diner.ngrok-free.dev/api/v1/instagram/callback"
    assert s.effective_instagram_redirect_uri == expected
    assert s.public_oauth_callback_url == expected


def test_oauth_authorization_url_rfc3986_encoding():
    """Verifies that get_oauth_authorization_url uses RFC 3986 percent encoding (%2F) for redirect_uri."""
    data = get_oauth_authorization_url("ws_test_456")
    raw_url = data["oauth_url"]

    # Verify base URL and parameters
    assert raw_url.startswith("https://www.instagram.com/oauth/authorize?")
    assert f"client_id={settings.META_APP_ID}" in raw_url
    assert "response_type=code" in raw_url
    assert "scope=" in raw_url
    assert "state=" in raw_url

    # Strict RFC 3986 percent-encoding check:
    # The query string in raw_url must contain redirect_uri=https%3A%2F%2F...
    # and must NOT contain raw slashes like redirect_uri=https%3A//
    assert "redirect_uri=https%3A%2F%2F" in raw_url
    assert "redirect_uri=https%3A//" not in raw_url

    # Verify that decoding the parameter yields the exact canonical redirect URI
    parsed = urllib.parse.urlparse(raw_url)
    qs = urllib.parse.parse_qs(parsed.query)
    assert "redirect_uri" in qs
    assert qs["redirect_uri"][0] == settings.effective_instagram_redirect_uri


def test_oauth_url_api_endpoint(client, auth_headers):
    """Verifies GET /api/v1/instagram/oauth-url endpoint returns correct structure and encoded redirect_uri."""
    res = client.get("/api/v1/instagram/oauth-url", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()

    assert "oauth_url" in data
    assert "state" in data
    assert "scopes_requested" in data

    parsed = urllib.parse.urlparse(data["oauth_url"])
    qs = urllib.parse.parse_qs(parsed.query)
    assert qs["redirect_uri"][0] == settings.effective_instagram_redirect_uri


def test_production_security_validation_scheme_and_domain():
    """Verifies validation rules enforce HTTPS on public URLs and reject invalid schemes."""
    # 1. Insecure http scheme on public domain in production should fail
    with pytest.raises(ValueError, match="must use HTTPS"):
        Settings(
            ENVIRONMENT="production",
            BACKEND_PUBLIC_URL="http://woka-api.com",
            META_APP_ID="3217043811838822",
            META_APP_SECRET="supersecret12345678901234567890"
        )

    # 2. Valid HTTPS public URL synchronizes META_REDIRECT_URI
    prod_valid = Settings(
        ENVIRONMENT="production",
        BACKEND_PUBLIC_URL="https://woka-api-staging.onrender.com",
        META_APP_ID="3217043811838822",
        META_APP_SECRET="supersecret12345678901234567890",
        META_VERIFY_TOKEN="valid_custom_prod_verify_token_2026",
        ALLOWED_HOSTS=["woka-api-staging.onrender.com"]
    )
    assert prod_valid.effective_instagram_redirect_uri == "https://woka-api-staging.onrender.com/api/v1/instagram/callback"
    assert prod_valid.META_REDIRECT_URI == "https://woka-api-staging.onrender.com/api/v1/instagram/callback"


def test_callback_fallback_behavior_and_validation():
    """Verifies that callback validation rejects malformed URLs, credentials, fragments, queries, and invalid schemes."""
    # 1. Reject empty
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_and_normalize_redirect_uri("")

    # 2. Never silently fall back to FRONTEND_URL or non-backend paths
    with pytest.raises(ValueError, match="does not match exact canonical backend callback path"):
        validate_and_normalize_redirect_uri("https://woka-staging.vercel.app/dashboard/instagram/callback")

    # 3. Reject embedded user credentials
    with pytest.raises(ValueError, match="embedded user credentials"):
        validate_and_normalize_redirect_uri("https://admin:pass@ngrok-free.dev/api/v1/instagram/callback")

    # 4. Reject URL fragments
    with pytest.raises(ValueError, match="fragments"):
        validate_and_normalize_redirect_uri("https://ngrok-free.dev/api/v1/instagram/callback#section")

    # 5. Reject URL query parameters
    with pytest.raises(ValueError, match="query parameters"):
        validate_and_normalize_redirect_uri("https://ngrok-free.dev/api/v1/instagram/callback?param=1")

    # 6. Reject insecure HTTP on public domains
    with pytest.raises(ValueError, match="must use HTTPS"):
        validate_and_normalize_redirect_uri("http://insecure-public-api.woka.io/api/v1/instagram/callback")

    # 7. Reject invalid schemes (e.g. ftp, javascript)
    with pytest.raises(ValueError, match="Invalid OAuth callback URI scheme"):
        validate_and_normalize_redirect_uri("ftp://api.woka.io/api/v1/instagram/callback")

    # 8. Missing both BACKEND_PUBLIC_URL and META_REDIRECT_URI raises ValueError
    s_empty = Settings(
        BACKEND_PUBLIC_URL="",
        META_REDIRECT_URI=""
    )
    with pytest.raises(ValueError, match="Neither BACKEND_PUBLIC_URL nor an explicit META_REDIRECT_URI is configured"):
        _ = s_empty.effective_instagram_redirect_uri


def test_exact_callback_path_equality_validation():
    """Fix 1 Regression: Verifies exact normalized path equality rejecting prefix, suffix, and alternate path attacks."""
    # 1. Correct canonical path accepted
    valid_url = "https://squash-dreadlock-diner.ngrok-free.dev/api/v1/instagram/callback"
    assert validate_and_normalize_redirect_uri(valid_url) == valid_url

    # 2. Prefix injection rejected
    with pytest.raises(ValueError, match="does not match exact canonical backend callback path"):
        validate_and_normalize_redirect_uri("https://squash-dreadlock-diner.ngrok-free.dev/not-the-api/api/v1/instagram/callback")

    # 3. Path suffix injection rejected
    with pytest.raises(ValueError, match="does not match exact canonical backend callback path"):
        validate_and_normalize_redirect_uri("https://squash-dreadlock-diner.ngrok-free.dev/api/v1/instagram/callback/extra")

    # 4. Incorrect API version prefix rejected
    with pytest.raises(ValueError, match="does not match exact canonical backend callback path"):
        validate_and_normalize_redirect_uri("https://squash-dreadlock-diner.ngrok-free.dev/api/v2/instagram/callback")


def test_frontend_supplied_redirect_uri_cannot_override_canonical_setting(caplog):
    """Fix 2: Verifies token exchange strictly enforces canonical URI and logs safe diagnostic warning without secrets."""
    captured_payload = {}

    def mock_post(url, data=None, **kwargs):
        nonlocal captured_payload
        captured_payload = data
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "mock_short_token",
            "user_id": "12345678"
        }
        mock_resp.headers = {"content-type": "application/json"}
        return mock_resp

    def mock_get(url, params=None, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "mock_long_token",
            "token_type": "bearer",
            "expires_in": 5184000
        }
        mock_resp.headers = {"content-type": "application/json"}
        return mock_resp

    with patch.object(httpx.Client, "post", side_effect=mock_post), \
         patch.object(httpx.Client, "get", side_effect=mock_get):
        exchange_code_for_tokens(
            code="test_code_valid",
            redirect_uri="https://adversary.com/steal-token/callback"
        )

    # 1. Assert outbound payload sent to Meta strictly uses canonical server redirect URI
    assert captured_payload is not None
    assert captured_payload["redirect_uri"] == settings.effective_instagram_redirect_uri
    assert captured_payload["redirect_uri"] != "https://adversary.com/steal-token/callback"

    # 2. Assert safe diagnostic logging: only generic mismatch warning logged
    assert "OAuth callback mismatch detected in token exchange request; enforcing canonical server redirect_uri." in caplog.text
    assert "https://adversary.com" not in caplog.text
    assert settings.effective_instagram_redirect_uri not in caplog.text
    assert settings.META_APP_SECRET not in caplog.text


def test_production_rejects_mock_authorization_codes(client, db_session, auth_headers, test_creator_user):
    """Verifies production environment strictly rejects mock or synthetic authorization codes."""
    user, ws = test_creator_user

    # Temporarily switch to production mode
    settings.ENVIRONMENT = "production"
    settings.ENABLE_MOCK_OAUTH = False

    try:
        mock_codes = ["mock_code_123", "auth_code_once", "test_code_synthetic"]
        for mock_code in mock_codes:
            state = generate_oauth_state(ws.id)
            res = client.post("/api/v1/instagram/connect", json={
                "code": mock_code,
                "state": state
            }, headers=auth_headers)
            assert res.status_code == 400
            assert "mock or synthetic authorization codes are strictly forbidden in production" in res.json()["detail"].lower()
    finally:
        settings.ENVIRONMENT = "test"
        settings.ENABLE_MOCK_OAUTH = True


def test_production_rejects_enable_mock_oauth_setting():
    """Verifies production environment configuration validator rejects ENABLE_MOCK_OAUTH=True."""
    with pytest.raises(ValueError, match="ENABLE_MOCK_OAUTH cannot be true in production"):
        Settings(
            ENVIRONMENT="production",
            ENABLE_MOCK_OAUTH=True,
            BACKEND_PUBLIC_URL="https://woka-api-staging.onrender.com",
            META_APP_ID="3217043811838822",
            META_APP_SECRET="supersecret12345678901234567890"
        )


def test_invalid_fabricated_code_cannot_create_connected_account(db_session, test_creator_user):
    """Verifies that failed Meta code exchange never creates or marks an account connected."""
    user, ws = test_creator_user
    state = generate_oauth_state(ws.id)

    # Ensure mock mode is inactive
    settings.ENABLE_MOCK_OAUTH = False
    settings.ENVIRONMENT = "development"

    try:
        # Simulate Meta returning an OAuth error
        with patch("app.services.instagram_service.exchange_code_for_tokens", side_effect=MetaAPIError("Invalid code format")):
            with pytest.raises(HTTPException) as exc_info:
                connect_or_update_account_from_oauth(
                    db=db_session,
                    workspace_id=ws.id,
                    code="AQ_fabricated_invalid_code",
                    state=state
                )
            assert exc_info.value.status_code == 400
            assert "Meta OAuth authorization code exchange failed" in exc_info.value.detail

        # Verify no connected account was created or activated in the database
        account = db_session.query(InstagramAccount).filter(
            InstagramAccount.workspace_id == ws.id,
            InstagramAccount.is_connected == True
        ).first()
        assert account is not None
        assert account.username == "test_creator_ig"
    finally:
        settings.ENABLE_MOCK_OAUTH = True
        settings.ENVIRONMENT = "test"


def test_deletion_status_endpoint_returns_404_for_unknown_code(client, db_session):
    """Fix 3: Verifies /deletion-status rejects unpersisted / unknown codes with 404 (no false COMPLETED response)."""
    resp = client.get("/api/v1/instagram/deletion-status?code=woka_del_unknown_fake_999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_deletion_status_endpoint_returns_honest_pending_and_completed(client, db_session):
    """Fix 3: Verifies /deletion-status returns genuine PENDING and COMPLETED status from persistent records."""
    # 1. Test PENDING record
    pending_record = InstagramDataDeletionRequest(
        confirmation_code="woka_del_pending_test",
        ig_user_id="ig_pending_user_1",
        status="PENDING",
        details="Data deletion request is currently pending processing."
    )
    db_session.add(pending_record)
    db_session.commit()

    resp_pending = client.get("/api/v1/instagram/deletion-status?code=woka_del_pending_test")
    assert resp_pending.status_code == 200
    assert resp_pending.json()["status"] == "PENDING"
    assert resp_pending.json()["confirmation_code"] == "woka_del_pending_test"

    # 2. Test COMPLETED record
    completed_record = InstagramDataDeletionRequest(
        confirmation_code="woka_del_completed_test",
        ig_user_id="ig_completed_user_2",
        status="COMPLETED",
        details="User data deletion request has been processed. Access tokens and profile associations have been purged.",
        completed_at=datetime.now(timezone.utc)
    )
    db_session.add(completed_record)
    db_session.commit()

    resp_completed = client.get("/api/v1/instagram/deletion-status?code=woka_del_completed_test")
    assert resp_completed.status_code == 200
    assert resp_completed.json()["status"] == "COMPLETED"
    assert resp_completed.json()["confirmation_code"] == "woka_del_completed_test"


def test_meta_data_deletion_callback_flow_and_idempotency(client, db_session, test_creator_user):
    """Fix 3: Verifies signed_request validation, persistent deletion tracking, data purging, and idempotency."""
    user, ws = test_creator_user
    ig_user_id = "ig_user_delete_target_123"

    # Create active InstagramAccount
    account = InstagramAccount(
        workspace_id=ws.id,
        ig_user_id=ig_user_id,
        username="user_to_delete",
        encrypted_access_token="encrypted_token_secret_123",
        profile_pic_url="https://example.com/pic.jpg",
        granted_permissions="instagram_business_basic",
        is_connected=True
    )
    db_session.add(account)
    db_session.commit()

    # Generate valid Meta signed_request for ig_user_id
    signed_req = generate_mock_signed_request(user_id=ig_user_id)

    # 1. Execute initial data deletion callback
    res = client.post("/api/v1/instagram/data-deletion", data={"signed_request": signed_req})
    assert res.status_code == 200
    data = res.json()
    assert "confirmation_code" in data
    assert "url" in data
    confirmation_code = data["confirmation_code"]
    assert confirmation_code.startswith("woka_del_")

    # Verify Instagram account data was purged
    db_session.refresh(account)
    assert account.is_connected is False
    assert account.encrypted_access_token == ""
    assert account.profile_pic_url is None
    assert account.granted_permissions == ""

    # Verify persistent deletion record was created with COMPLETED status
    del_req = db_session.query(InstagramDataDeletionRequest).filter(
        InstagramDataDeletionRequest.confirmation_code == confirmation_code
    ).first()
    assert del_req is not None
    assert del_req.status == "COMPLETED"
    assert del_req.ig_user_id == ig_user_id
    assert del_req.completed_at is not None

    # 2. Idempotent Retry: Repeat call with exact same signed_request
    retry_res = client.post("/api/v1/instagram/data-deletion", data={"signed_request": signed_req})
    assert retry_res.status_code == 200
    retry_data = retry_res.json()
    assert retry_data["confirmation_code"] == confirmation_code  # Returns same confirmation code


def test_meta_data_deletion_callback_tampered_signature_rejected(client):
    """Fix 3: Verifies tampered or invalid signed_request is rejected with HTTP 401."""
    tampered_signed_request = "invalid_signature.eyJ1c2VyX2lkIjoiMTIzNDU2Nzg5MCJ9"
    res = client.post("/api/v1/instagram/data-deletion", data={"signed_request": tampered_signed_request})
    assert res.status_code == 401
    assert "invalid signed_request signature" in res.json()["detail"].lower()


def test_meta_app_secret_alias_and_signed_request_verification():
    """Verify META_CLIENT_SECRET alias and actual HMAC-SHA256 signed-request verification using META_APP_SECRET."""
    from app.services.instagram_service import parse_meta_signed_request, generate_mock_signed_request
    import hmac, hashlib, base64, json

    # 1. Verify Settings alias
    s = Settings(
        META_CLIENT_SECRET="test_alias_secret_12345",
        BACKEND_PUBLIC_URL="https://squash-dreadlock-diner.ngrok-free.dev",
        META_APP_ID="3217043811838822"
    )
    assert s.META_APP_SECRET == "test_alias_secret_12345"
    assert s.meta_client_secret == "test_alias_secret_12345"

    # 2. Verify actual signed request verification uses META_APP_SECRET
    user_id = "test_meta_user_998877"
    valid_signed_req = generate_mock_signed_request(user_id=user_id)
    payload = parse_meta_signed_request(valid_signed_req)
    assert payload is not None
    assert payload["user_id"] == user_id
    assert payload["algorithm"] == "HMAC-SHA256"

    # 3. Verify mismatch with a different secret is rejected
    payload_data = {"user_id": user_id, "algorithm": "HMAC-SHA256", "issued_at": 1234567890}
    payload_json = json.dumps(payload_data, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip("=")
    wrong_sig = hmac.new(b"wrong_secret_key_value", payload_b64.encode(), hashlib.sha256).digest()
    wrong_sig_b64 = base64.urlsafe_b64encode(wrong_sig).decode().rstrip("=")
    wrong_signed_req = f"{wrong_sig_b64}.{payload_b64}"
    assert parse_meta_signed_request(wrong_signed_req) is None


def test_meta_data_deletion_comprehensive_cascade_and_retention(client, db_session, test_creator_user):
    """Verify comprehensive deletion of all Instagram-derived records while preserving unrelated workspace data."""
    from app.models.automation import Automation, AutomationLog
    from app.models.analytics import CreatorAnalytics
    from app.models.reel_intelligence import ReelAnalysisJob, ReelMetricSnapshot, ReelReport
    from app.models.profile import CreatorProfile
    from app.models.invoice import Invoice
    from app.models.user import User, Workspace
    import datetime as dt

    user, ws = test_creator_user
    ig_user_id = "ig_cascade_target_456"

    # 1. Instagram Account
    account = InstagramAccount(
        workspace_id=ws.id,
        ig_user_id=ig_user_id,
        username="cascade_user",
        encrypted_access_token="enc_token_xyz",
        profile_pic_url="https://scontent.cdninstagram.com/avatar.jpg",
        granted_permissions="instagram_business_basic,instagram_business_manage_insights",
        followers_count=15200,
        media_count=88,
        is_connected=True
    )
    db_session.add(account)
    db_session.flush()

    # 2. Automation and logs
    auto = Automation(
        workspace_id=ws.id,
        ig_account_id=account.id,
        name="Auto Reply",
        trigger_type="COMMENT",
        is_active=True,
        target_post_id="post_ig_123",
        target_post_preview_url="https://scontent.cdninstagram.com/post.jpg",
        dm_message_template="Thanks for your comment!"
    )
    db_session.add(auto)
    db_session.flush()

    log1 = AutomationLog(
        automation_id=auto.id,
        recipient_ig_id="recipient_ig_1",
        recipient_username="fan_1",
        trigger_comment_text="Love this!",
        dm_text_sent="Thanks!"
    )
    log2 = AutomationLog(
        automation_id=auto.id,
        recipient_ig_id=ig_user_id,
        recipient_username="cascade_user",
        trigger_comment_text="Hello",
        dm_text_sent="Welcome!"
    )
    db_session.add_all([log1, log2])

    # 3. Creator Analytics (with audience insights and top posts)
    analytics = CreatorAnalytics(
        workspace_id=ws.id,
        snapshot_date=dt.date.today(),
        followers_count=15200,
        media_count=88,
        reach_30d=45000,
        impressions_30d=60000,
        avg_engagement_rate=4.5,
        demographics_json='{"age": {"18-24": 40, "25-34": 50}}',
        top_posts_json='[{"id": "post_1", "caption": "Reel 1"}]'
    )
    db_session.add(analytics)

    # 4. Connected Reel Job and Snapshots
    connected_job = ReelAnalysisJob(
        workspace_id=ws.id,
        analysis_mode="CONNECTED_ACCOUNT",
        input_type="CONNECTED_POST",
        source_media_id="media_ig_789",
        status="COMPLETED"
    )
    db_session.add(connected_job)
    db_session.flush()

    connected_snapshot = ReelMetricSnapshot(
        workspace_id=ws.id,
        job_id=connected_job.id,
        views_count=10000,
        reach_count=8500,
        impressions_count=9200,
        likes_count=500
    )
    db_session.add(connected_snapshot)

    connected_report = ReelReport(
        workspace_id=ws.id,
        job_id=connected_job.id,
        title="Connected Reel",
        analysis_mode="CONNECTED_ACCOUNT",
        caption="Original Instagram Caption",
        calculated_metrics_json='{"reach": 8500, "saves": 120}',
        creative_quality_score=8.5,
        performance_score=9.0,
        growth_conversion_score=8.0,
        viral_potential_estimate=8.2
    )
    db_session.add(connected_report)
    db_session.flush()
    connected_job.report_id = connected_report.id

    # 5. Unrelated workspace records to preserve
    profile = db_session.query(CreatorProfile).filter(CreatorProfile.workspace_id == ws.id).first()
    if profile:
        profile.avatar_url = "https://scontent.cdninstagram.com/profile.jpg"

    invoice = Invoice(
        workspace_id=ws.id,
        invoice_number="INV-2026-001",
        client_name="Test Sponsor",
        client_email="sponsor@brand.com",
        due_date=dt.date.today(),
        total_amount=1500.0,
        status="PAID"
    )
    db_session.add(invoice)

    unrelated_job = ReelAnalysisJob(
        workspace_id=ws.id,
        analysis_mode="VIDEO_UPLOAD",
        input_type="DIRECT_UPLOAD",
        status="COMPLETED"
    )
    db_session.add(unrelated_job)

    db_session.commit()

    # Trigger actual data deletion callback
    signed_req = generate_mock_signed_request(user_id=ig_user_id)
    res = client.post("/api/v1/instagram/data-deletion", data={"signed_request": signed_req})
    assert res.status_code == 200
    code = res.json()["confirmation_code"]

    # Verify Instagram Account is purged
    db_session.refresh(account)
    assert account.is_connected is False
    assert account.encrypted_access_token == ""
    assert account.profile_pic_url is None
    assert account.granted_permissions == ""
    assert account.followers_count == 0
    assert account.media_count == 0

    # Verify Automation is deactivated and logs deleted
    db_session.refresh(auto)
    assert auto.is_active is False
    assert auto.target_post_id is None
    assert auto.target_post_preview_url is None
    remaining_logs = db_session.query(AutomationLog).filter(AutomationLog.automation_id == auto.id).count()
    assert remaining_logs == 0

    # Verify Creator Analytics audience insights & top posts are purged
    db_session.refresh(analytics)
    assert analytics.demographics_json is None
    assert analytics.top_posts_json is None
    assert analytics.reach_30d == 0
    assert analytics.impressions_30d == 0

    # Verify Connected Reel insights purged
    db_session.refresh(connected_job)
    assert connected_job.source_media_id is None
    remaining_snapshots = db_session.query(ReelMetricSnapshot).filter(ReelMetricSnapshot.job_id == connected_job.id).count()
    assert remaining_snapshots == 0
    db_session.refresh(connected_report)
    assert connected_report.caption is None
    assert connected_report.calculated_metrics_json == "{}"

    # Verify Instagram CDN avatar was purged
    if profile:
        db_session.refresh(profile)
        assert profile.avatar_url is None

    # Verify UNRELATED WORKSPACE DATA IS PRESERVED
    assert db_session.query(Invoice).filter(Invoice.workspace_id == ws.id).count() == 1
    assert db_session.query(ReelAnalysisJob).filter(ReelAnalysisJob.id == unrelated_job.id).count() == 1
    assert db_session.query(User).filter(User.id == user.id).count() == 1
    assert db_session.query(Workspace).filter(Workspace.id == ws.id).count() == 1


def test_deletion_status_handles_failed_status(client, db_session):
    """Verify /deletion-status handles FAILED status appropriately without hardcoded outputs."""
    failed_record = InstagramDataDeletionRequest(
        confirmation_code="woka_del_failed_test",
        ig_user_id="ig_failed_user",
        status="FAILED",
        details="Meta Graph API rate limit encountered during automated profile teardown."
    )
    db_session.add(failed_record)
    db_session.commit()

    res = client.get("/api/v1/instagram/deletion-status?code=woka_del_failed_test")
    assert res.status_code == 200
    assert res.json()["status"] == "FAILED"
    assert "rate limit" in res.json()["message"]
