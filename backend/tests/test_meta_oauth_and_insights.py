import json
import os
import time
from datetime import datetime, timezone, timedelta
import pytest
from unittest.mock import patch, MagicMock
import httpx

from app.config import settings
from app.models.instagram import InstagramAccount
from app.models.reel_intelligence import ReelMetricSnapshot
from app.models.user import User, Workspace, WorkspaceMember
from app.models.subscription import Subscription
from app.security import encrypt_token, decrypt_token, create_access_token, get_password_hash, reset_rate_limits
from app.services.instagram_service import (
    generate_oauth_state,
    verify_oauth_state,
    exchange_code_for_tokens,
    refresh_long_lived_token,
    fetch_instagram_user_profile,
    fetch_instagram_media_list,
    fetch_media_insights,
    _request_with_retry,
    MetaAPIError,
    MetaTokenExpiredError,
    MetaPermissionError,
    MetaRateLimitError
)

# ==============================================================================
# 1. Cryptographic State & CSRF / Replay Protection Tests
# ==============================================================================

def test_oauth_state_generation_and_verification(db_session):
    workspace_id = "ws_test_state_123"
    state = generate_oauth_state(workspace_id)
    
    assert "." in state
    assert verify_oauth_state(state, workspace_id, db=db_session) is True


def test_oauth_state_rejects_tampered_signature(db_session):
    workspace_id = "ws_test_state_123"
    state = generate_oauth_state(workspace_id)
    payload_b64, sig = state.split(".", 1)
    
    # Tamper with the signature
    tampered_sig = sig[:-4] + "abcd"
    tampered_state = f"{payload_b64}.{tampered_sig}"
    
    assert verify_oauth_state(tampered_state, workspace_id, db=db_session) is False


def test_oauth_state_rejects_workspace_mismatch(db_session):
    state = generate_oauth_state("ws_original")
    assert verify_oauth_state(state, "ws_different_attacker", db=db_session) is False


def test_oauth_state_rejects_expired_timestamp(db_session):
    import base64, hmac, hashlib
    workspace_id = "ws_expired_test"
    expired_payload = {
        "workspace_id": workspace_id,
        "timestamp": int(datetime.now(timezone.utc).timestamp()) - 1000,
        "nonce": "test-nonce-expired"
    }
    raw_json = json.dumps(expired_payload, separators=(",", ":"))
    sig = hmac.new(settings.SECRET_KEY.encode(), raw_json.encode(), hashlib.sha256).hexdigest()
    b64_payload = base64.urlsafe_b64encode(raw_json.encode()).decode()
    expired_state = f"{b64_payload}.{sig}"
    
    assert verify_oauth_state(expired_state, workspace_id, db=db_session) is False


def test_oauth_state_replay_attack_prevention(db_session):
    workspace_id = "ws_replay_prevention"
    state = generate_oauth_state(workspace_id)
    
    # First verification should succeed
    assert verify_oauth_state(state, workspace_id, db=db_session) is True
    
    # Second verification with same state/nonce must fail (replay attack rejected)
    assert verify_oauth_state(state, workspace_id, db=db_session) is False


# ==============================================================================
# 2. Token Lifecycle Unit Tests (Code Exchange, Long-Lived Token, Refresh)
# ==============================================================================

def test_exchange_code_for_tokens_success():
    short_lived_resp = MagicMock()
    short_lived_resp.status_code = 200
    short_lived_resp.json.return_value = {
        "access_token": "ig_short_lived_test_token",
        "user_id": "17841400000000001",
        "permissions": ["instagram_business_basic", "instagram_business_manage_insights"]
    }

    long_lived_resp = MagicMock()
    long_lived_resp.status_code = 200
    long_lived_resp.json.return_value = {
        "access_token": "ig_long_lived_60day_test_token",
        "token_type": "bearer",
        "expires_in": 5184000
    }

    def mock_request(url, *args, **kwargs):
        if "oauth/access_token" in str(url):
            return short_lived_resp
        return long_lived_resp

    with patch.object(httpx.Client, "post", side_effect=mock_request), \
         patch.object(httpx.Client, "get", side_effect=mock_request):
        token_info = exchange_code_for_tokens("mock_auth_code_xyz")
        assert token_info["access_token"] == "ig_long_lived_60day_test_token"
        assert token_info["user_id"] == "17841400000000001"
        assert token_info["expires_in"] == 5184000


def test_exchange_code_failure_raises_meta_api_error():
    err_resp = MagicMock()
    err_resp.status_code = 400
    err_resp.headers = {"content-type": "application/json"}
    err_resp.json.return_value = {
        "error_type": "OAuthException",
        "code": 400,
        "error_message": "Invalid verification code format."
    }

    with patch.object(httpx.Client, "post", return_value=err_resp):
        with pytest.raises(MetaAPIError) as exc_info:
            exchange_code_for_tokens("invalid_code_123")
        assert "Invalid verification code format" in str(exc_info.value)


def test_refresh_long_lived_token_success():
    refresh_resp = MagicMock()
    refresh_resp.status_code = 200
    refresh_resp.json.return_value = {
        "access_token": "ig_refreshed_long_lived_token_999",
        "token_type": "bearer",
        "expires_in": 5184000
    }

    with patch.object(httpx.Client, "get", return_value=refresh_resp):
        result = refresh_long_lived_token("existing_token_xyz")
        assert result["access_token"] == "ig_refreshed_long_lived_token_999"
        assert result["expires_in"] == 5184000


def test_refresh_token_expired_raises_meta_token_expired_error():
    err_resp = MagicMock()
    err_resp.status_code = 400
    err_resp.headers = {"content-type": "application/json"}
    err_resp.json.return_value = {
        "error": {
            "message": "Error validating access token: Session has expired.",
            "type": "OAuthException",
            "code": 190,
            "error_subcode": 463
        }
    }

    with patch.object(httpx.Client, "get", return_value=err_resp):
        with pytest.raises(MetaTokenExpiredError) as exc_info:
            refresh_long_lived_token("expired_token")
        assert "expired" in str(exc_info.value).lower()


# ==============================================================================
# 3. Media Insights & Error Mapping Unit Tests
# ==============================================================================

def test_fetch_media_insights_success():
    insights_resp = MagicMock()
    insights_resp.status_code = 200
    insights_resp.json.return_value = {
        "data": [
            {"name": "reach", "period": "lifetime", "values": [{"value": 25400}]},
            {"name": "saved", "period": "lifetime", "values": [{"value": 940}]},
            {"name": "shares", "period": "lifetime", "values": [{"value": 410}]},
            {"name": "total_interactions", "period": "lifetime", "values": [{"value": 3150}]}
        ]
    }

    with patch.object(httpx.Client, "get", return_value=insights_resp):
        insights = fetch_media_insights("valid_token", "media_reel_999")
        assert insights["reach"] == 25400
        assert insights["saved"] == 940
        assert insights["shares"] == 410
        assert insights["total_interactions"] == 3150


def test_fetch_media_insights_rate_limit_error():
    rate_resp = MagicMock()
    rate_resp.status_code = 400
    rate_resp.headers = {"content-type": "application/json"}
    rate_resp.json.return_value = {
        "error": {
            "message": "User request limit reached",
            "type": "OAuthException",
            "code": 17
        }
    }

    with patch.object(httpx.Client, "get", return_value=rate_resp):
        with pytest.raises(MetaRateLimitError):
            fetch_media_insights("valid_token", "media_reel_999")


def test_fetch_media_insights_permission_error():
    perm_resp = MagicMock()
    perm_resp.status_code = 403
    perm_resp.headers = {"content-type": "application/json"}
    perm_resp.json.return_value = {
        "error": {
            "message": "Requires instagram_business_manage_insights permission",
            "type": "OAuthException",
            "code": 10
        }
    }

    with patch.object(httpx.Client, "get", return_value=perm_resp):
        with pytest.raises(MetaPermissionError):
            fetch_media_insights("valid_token", "media_reel_999")


# ==============================================================================
# 4. API Endpoints Integration Tests (OAuth, Status, Sync, Disconnect, Refresh)
# ==============================================================================

def test_get_oauth_url_endpoint(client, auth_headers):
    resp = client.get("/api/v1/instagram/oauth-url", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "oauth_url" in data
    assert "instagram_business_manage_insights" in data["oauth_url"]
    assert "instagram_business_basic" in data["oauth_url"]
    assert "state=" in data["oauth_url"]
    assert data["expires_in_seconds"] == 900


def test_connect_account_endpoint_with_mocked_meta_exchange(client, auth_headers, test_creator_user):
    user, ws = test_creator_user
    state = generate_oauth_state(ws.id)

    mock_token_data = {
        "access_token": "ig_live_token_for_connect_test",
        "user_id": "17841499999999999",
        "expires_in": 5184000,
        "permissions": ["instagram_business_basic", "instagram_business_manage_insights"]
    }
    mock_profile_data = {
        "id": "17841499999999999",
        "username": "live_creator_connected",
        "name": "Live Creator",
        "profile_picture_url": "https://example.com/pic.jpg"
    }

    with patch("app.services.instagram_service.exchange_code_for_tokens", return_value=mock_token_data), \
         patch("app.services.instagram_service.fetch_instagram_user_profile", return_value=mock_profile_data):
        
        resp = client.post(
            "/api/v1/instagram/connect",
            json={"code": "meta_auth_code_valid", "state": state},
            headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "live_creator_connected"
        assert data["is_connected"] is True
        assert data["is_sandbox"] is False
        assert "instagram_business_manage_insights" in data["granted_permissions"]


def test_connect_account_rejects_invalid_csrf_state(client, auth_headers):
    resp = client.post(
        "/api/v1/instagram/connect",
        json={"code": "valid_code", "state": "invalid.csrf.signature"},
        headers=auth_headers
    )
    assert resp.status_code == 400
    assert "CSRF protection failed" in resp.json()["detail"]


def test_instagram_status_endpoint(client, auth_headers, test_creator_user):
    user, ws = test_creator_user
    resp = client.get("/api/v1/instagram/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_connected"] is True
    assert data["has_insights_permission"] is True
    assert data["token_status"] == "ACTIVE"
    assert data["api_version"] == "v21.0"


def test_instagram_status_reports_expired_token(client, auth_headers, db_session, test_creator_user):
    user, ws = test_creator_user
    account = db_session.query(InstagramAccount).filter(InstagramAccount.workspace_id == ws.id).first()
    # Force expired token
    account.token_expires_at = datetime.now(timezone.utc) - timedelta(days=2)
    db_session.commit()

    resp = client.get("/api/v1/instagram/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_connected"] is False
    assert data["token_status"] == "EXPIRED"


def test_sync_insights_live_persists_snapshots(client, auth_headers, db_session, test_creator_user):
    user, ws = test_creator_user
    account = db_session.query(InstagramAccount).filter(InstagramAccount.workspace_id == ws.id).first()
    account.is_sandbox = False
    account.encrypted_access_token = encrypt_token("valid_live_token_123")
    account.token_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    db_session.commit()

    mock_media = [
        {
            "id": "reel_live_101",
            "caption": "Testing live insights sync",
            "media_type": "VIDEO",
            "media_product_type": "REELS",
            "like_count": 450,
            "comments_count": 32,
            "timestamp": "2026-10-14T10:00:00Z"
        }
    ]
    mock_insights = {
        "reach": 12800,
        "saved": 310,
        "shares": 195,
        "total_interactions": 955
    }

    with patch("app.services.instagram_service.fetch_instagram_user_profile", return_value={"username": "live_user", "name": "Live"}), \
         patch("app.services.instagram_service.fetch_instagram_media_list", return_value=mock_media), \
         patch("app.services.instagram_service.fetch_media_insights", return_value=mock_insights):
        
        resp = client.post("/api/v1/instagram/sync-insights", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert data["synced_media_count"] == 1
        assert data["metric_snapshots_created"] == 1
        assert data["provenance"]["mode"] == "META_GRAPH_API_LIVE"

        # Verify persisted snapshot in database
        snapshot = db_session.query(ReelMetricSnapshot).filter(
            ReelMetricSnapshot.workspace_id == ws.id,
            ReelMetricSnapshot.source_type == "META_GRAPH_API"
        ).first()
        assert snapshot is not None
        assert snapshot.reach_count == 12800
        assert snapshot.saves_count == 310
        assert snapshot.shares_count == 195


def test_sync_insights_handles_expired_token(client, auth_headers, db_session, test_creator_user):
    user, ws = test_creator_user
    account = db_session.query(InstagramAccount).filter(InstagramAccount.workspace_id == ws.id).first()
    account.is_sandbox = False
    account.encrypted_access_token = encrypt_token("expired_live_token")
    account.token_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    db_session.commit()

    with patch("app.services.instagram_service.fetch_instagram_user_profile", side_effect=MetaTokenExpiredError("Token expired", code=190)):
        resp = client.post("/api/v1/instagram/sync-insights", headers=auth_headers)
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()

        # Account should be marked as disconnected
        db_session.refresh(account)
        assert account.is_connected is False


def test_sync_insights_handles_rate_limit(client, auth_headers, db_session, test_creator_user):
    user, ws = test_creator_user
    account = db_session.query(InstagramAccount).filter(InstagramAccount.workspace_id == ws.id).first()
    account.is_sandbox = False
    account.encrypted_access_token = encrypt_token("valid_token")
    account.token_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    db_session.commit()

    with patch("app.services.instagram_service.fetch_instagram_user_profile", side_effect=MetaRateLimitError("Rate limit reached", code=17)):
        resp = client.post("/api/v1/instagram/sync-insights", headers=auth_headers)
        assert resp.status_code == 429
        assert "rate limit" in resp.json()["detail"].lower()


def test_refresh_token_endpoint(client, auth_headers, db_session, test_creator_user):
    user, ws = test_creator_user
    account = db_session.query(InstagramAccount).filter(InstagramAccount.workspace_id == ws.id).first()
    account.is_sandbox = False
    account.encrypted_access_token = encrypt_token("token_to_refresh")
    account.token_expires_at = datetime.now(timezone.utc) + timedelta(days=5)
    db_session.commit()

    mock_refresh_result = {
        "access_token": "newly_refreshed_access_token_12345",
        "expires_in": 5184000
    }

    with patch("app.services.instagram_service.refresh_long_lived_token", return_value=mock_refresh_result):
        resp = client.post("/api/v1/instagram/refresh-token", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert "refreshed" in data["message"]

        db_session.refresh(account)
        decrypted = decrypt_token(account.encrypted_access_token)
        assert decrypted == "newly_refreshed_access_token_12345"


def test_disconnect_instagram_account(client, auth_headers, db_session, test_creator_user):
    user, ws = test_creator_user
    resp = client.post("/api/v1/instagram/disconnect", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "DISCONNECTED"

    account = db_session.query(InstagramAccount).filter(InstagramAccount.workspace_id == ws.id).first()
    assert account.is_connected is False
    assert account.encrypted_access_token == ""


# ==============================================================================
# 5. Strict Cross-Tenant Isolation Tests
# ==============================================================================

def test_tenant_isolation_cannot_access_or_disconnect_other_tenant_instagram(client, db_session, test_creator_user):
    creator_user, creator_ws = test_creator_user

    # Create attacker tenant user and workspace
    attacker = User(
        email="attacker@rivalcorp.com",
        hashed_password=get_password_hash("AttackerPass123!"),
        full_name="Attacker",
        role="CREATOR"
    )
    db_session.add(attacker)
    db_session.flush()

    attacker_ws = Workspace(name="Attacker Workspace", owner_id=attacker.id)
    db_session.add(attacker_ws)
    db_session.flush()

    db_session.add(WorkspaceMember(workspace_id=attacker_ws.id, user_id=attacker.id, role_in_workspace="OWNER"))
    db_session.add(Subscription(workspace_id=attacker_ws.id, plan_tier="FREE", status="ACTIVE"))
    db_session.commit()

    attacker_token = create_access_token(data={"sub": attacker.id, "role": attacker.role, "workspace_id": attacker_ws.id})
    attacker_headers = {"Authorization": f"Bearer {attacker_token}"}

    # Attacker checks status -> should show not connected (cannot see creator's account)
    status_resp = client.get("/api/v1/instagram/status", headers=attacker_headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["is_connected"] is False

    # Attacker tries to sync insights -> fails because attacker has no connected account
    sync_resp = client.post("/api/v1/instagram/sync-insights", headers=attacker_headers)
    assert sync_resp.status_code == 400
    assert "No active Instagram account connected" in sync_resp.json()["detail"]

    # Attacker tries to disconnect -> only disconnects attacker's (nonexistent) account, creator's remains untouched
    disc_resp = client.post("/api/v1/instagram/disconnect", headers=attacker_headers)
    assert disc_resp.status_code == 200

    creator_account = db_session.query(InstagramAccount).filter(InstagramAccount.workspace_id == creator_ws.id).first()
    assert creator_account.is_connected is True


# ==============================================================================
# 6. GET Callback Browser Redirects & Resiliency Tests
# ==============================================================================

def test_oauth_get_callback_success_redirect(client, db_session, test_creator_user):
    reset_rate_limits()
    user, ws = test_creator_user
    state = generate_oauth_state(ws.id)

    mock_tokens = {
        "access_token": "mock_60d_token_for_redirect",
        "user_id": "17841400000000001",
        "expires_in": 5184000,
        "permissions": ["instagram_business_basic", "instagram_business_manage_insights"]
    }
    mock_profile = {
        "id": "17841400000000001",
        "username": "browser_redirect_creator",
        "name": "Browser Creator",
        "account_type": "BUSINESS",
        "media_count": 24
    }

    with patch("app.services.instagram_service.exchange_code_for_tokens", return_value=mock_tokens), \
         patch("app.services.instagram_service.fetch_instagram_user_profile", return_value=mock_profile):
        
        resp = client.get(
            f"/api/v1/instagram/callback?code=live_auth_code_789&state={state}",
            follow_redirects=False
        )
        assert resp.status_code == 302
        location = resp.headers.get("location", "")
        assert f"{settings.FRONTEND_URL}/dashboard/instagram" in location
        assert "connected=true" in location
        assert "browser_redirect_creator" in location

        # Verify database record updated
        account = db_session.query(InstagramAccount).filter(InstagramAccount.workspace_id == ws.id).first()
        assert account is not None
        assert account.is_connected is True
        assert account.username == "browser_redirect_creator"


def test_oauth_get_callback_user_cancellation_redirect(client):
    reset_rate_limits()
    resp = client.get(
        "/api/v1/instagram/callback?error=access_denied&error_reason=user_denied&error_description=Permissions+error",
        follow_redirects=False
    )
    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert f"{settings.FRONTEND_URL}/dashboard/instagram" in location
    assert "error=" in location
    assert "Permissions" in location


def test_oauth_get_callback_tampered_state(client):
    reset_rate_limits()
    resp = client.get(
        "/api/v1/instagram/callback?code=live_auth_code_789&state=tampered.fake_signature",
        follow_redirects=False
    )
    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert f"{settings.FRONTEND_URL}/dashboard/instagram" in location
    assert "error=" in location
    assert "tampered" in location.lower() or "invalid" in location.lower()


def test_oauth_get_callback_missing_code(client, test_creator_user):
    reset_rate_limits()
    user, ws = test_creator_user
    state = generate_oauth_state(ws.id)

    resp = client.get(
        f"/api/v1/instagram/callback?state={state}",
        follow_redirects=False
    )
    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert f"{settings.FRONTEND_URL}/dashboard/instagram" in location
    assert "error=" in location
    assert "missing" in location.lower()


# ==============================================================================
# 7. Media List Cursor Pagination & Network Retry Tests
# ==============================================================================

def test_fetch_instagram_media_list_pagination():
    page1_data = {
        "data": [
            {"id": "media_1", "caption": "Reel 1", "media_type": "VIDEO", "media_product_type": "REELS"},
            {"id": "media_2", "caption": "Reel 2", "media_type": "VIDEO", "media_product_type": "REELS"}
        ],
        "paging": {
            "cursors": {"after": "cursor_page_2"},
            "next": "https://graph.instagram.com/v21.0/me/media?after=cursor_page_2"
        }
    }
    page2_data = {
        "data": [
            {"id": "media_3", "caption": "Reel 3", "media_type": "VIDEO", "media_product_type": "REELS"},
            {"id": "media_4", "caption": "Reel 4", "media_type": "VIDEO", "media_product_type": "REELS"}
        ],
        "paging": {}
    }

    resp1 = MagicMock()
    resp1.status_code = 200
    resp1.json.return_value = page1_data

    resp2 = MagicMock()
    resp2.status_code = 200
    resp2.json.return_value = page2_data

    with patch("app.services.instagram_service._request_with_retry", side_effect=[resp1, resp2]):
        results = fetch_instagram_media_list("mock_token", limit=10, max_pages=2)
        assert len(results) == 4
        ids = [m["id"] for m in results]
        assert ids == ["media_1", "media_2", "media_3", "media_4"]


def test_bounded_retry_on_transient_500_error():
    resp_500 = MagicMock()
    resp_500.status_code = 500
    resp_500.headers = {"content-type": "application/json"}
    resp_500.json.return_value = {"error": {"message": "Transient Meta server failure", "code": 2}}

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {"data": []}

    with patch("httpx.Client.get", side_effect=[resp_500, resp_200]) as mock_get:
        resp = _request_with_retry("GET", "https://graph.instagram.com/test", max_retries=2, base_backoff_seconds=0.001)
        assert resp.status_code == 200
        assert mock_get.call_count == 2


def test_bounded_retry_exhaustion_on_network_timeout():
    with patch("httpx.Client.get", side_effect=httpx.ConnectTimeout("Connection timed out")) as mock_get:
        with pytest.raises(MetaAPIError) as exc_info:
            _request_with_retry("GET", "https://graph.instagram.com/test", max_retries=2, base_backoff_seconds=0.001)
        assert "Network error" in exc_info.value.message
        assert mock_get.call_count == 3


# ==============================================================================
# 8. Health & Readiness Probe Tests
# ==============================================================================

def test_container_health_probes(client):
    # Liveness probe
    liveness_resp = client.get("/healthz")
    assert liveness_resp.status_code == 200
    assert liveness_resp.json()["status"] == "alive"

    # Readiness probe (with DB ping)
    readiness_resp = client.get("/readyz")
    assert readiness_resp.status_code == 200
    assert readiness_resp.json()["status"] == "ready"
    assert readiness_resp.json()["database"] == "connected"

    # API v1 health
    v1_health = client.get("/api/v1/health")
    assert v1_health.status_code == 200
    assert v1_health.json()["status"] == "healthy"


# ==============================================================================
# 9. Opt-in Live Meta Graph API Integration Test
# ==============================================================================

LIVE_META_TESTING = os.getenv("TEST_LIVE_META_CREDENTIALS", "false").lower() == "true"

@pytest.mark.skipif(not LIVE_META_TESTING, reason="Live Meta API test skipped (TEST_LIVE_META_CREDENTIALS != 'true')")
def test_live_meta_graph_api_token_inspection():
    live_token = os.getenv("META_LIVE_TEST_TOKEN")
    assert live_token, "META_LIVE_TEST_TOKEN must be configured when TEST_LIVE_META_CREDENTIALS=true"
    profile = fetch_instagram_user_profile(live_token)
    assert "username" in profile
    assert "id" in profile
