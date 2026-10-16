import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone, timedelta
from app.config import settings
from app.services.instagram_service import generate_oauth_state, verify_oauth_state, parse_meta_signed_request
from app.models.subscription import Subscription
from app.models.instagram import InstagramAccount

def test_oauth_state_expiration(db_session, test_creator_user):
    user, ws = test_creator_user
    # 1. State with timestamp 20 minutes ago (1200s > 900s max age)
    expired_payload = {
        "workspace_id": ws.id,
        "timestamp": int(datetime.now(timezone.utc).timestamp()) - 1200,
        "nonce": "expired_nonce_123"
    }
    raw_json = json.dumps(expired_payload, separators=(",", ":"))
    sig = hmac.new(settings.SECRET_KEY.encode(), raw_json.encode(), hashlib.sha256).hexdigest()
    b64_payload = base64.urlsafe_b64encode(raw_json.encode()).decode()
    expired_state = f"{b64_payload}.{sig}"

    # Must be rejected due to expiration
    is_valid = verify_oauth_state(expired_state, ws.id, db=db_session)
    assert is_valid is False

def test_oauth_state_nonce_replay_prevention(client, db_session, auth_headers, test_creator_user):
    user, ws = test_creator_user
    # Generate fresh signed state
    valid_state = generate_oauth_state(ws.id)

    # 1. First verification / connect succeeds
    res1 = client.post("/api/v1/instagram/connect", json={
        "code": "auth_code_once",
        "state": valid_state
    }, headers=auth_headers)
    assert res1.status_code == 200

    # 2. Replay attack: reusing the same state parameter must be blocked
    res2 = client.post("/api/v1/instagram/connect", json={
        "code": "auth_code_once",
        "state": valid_state
    }, headers=auth_headers)
    assert res2.status_code == 400
    assert "csrf protection failed" in res2.json()["detail"].lower()

def test_monthly_quota_enforcement(client, db_session, auth_headers, test_creator_user):
    user, ws = test_creator_user
    # Set subscription quota to exhausted (50/50 used)
    sub = db_session.query(Subscription).filter(Subscription.workspace_id == ws.id).first()
    sub.dm_limit_monthly = 50
    sub.dm_used_monthly = 50
    db_session.commit()

    # Create automation rule
    client.post("/api/v1/automations", json={
        "name": "Promo Code",
        "trigger_type": "COMMENT",
        "target_post_type": "ALL_POSTS",
        "match_type": "CONTAINS_ANY",
        "trigger_keywords": ["promo"],
        "dm_message_template": "Here is promo code!",
        "is_active": True,
        "cooldown_minutes": 60
    }, headers=auth_headers)

    # Send incoming comment webhook
    webhook_payload = {
        "object": "instagram",
        "entry": [{
            "id": "ig_test_user_id",
            "changes": [{
                "field": "comments",
                "value": {
                    "id": "quota_test_comment_001",
                    "text": "Give me the promo please!",
                    "from": {"id": "fan_quota_1", "username": "fan_quota"}
                }
            }]
        }]
    }
    raw = json.dumps(webhook_payload).encode()
    sig = "sha256=" + hmac.new(settings.META_APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()

    res = client.post("/api/v1/instagram/webhook", content=raw, headers={"X-Hub-Signature-256": sig})
    assert res.status_code == 200
    assert res.json()["results"][0]["status"] == "QUOTA_EXCEEDED"

def test_meta_deauthorize_callback(client, db_session, test_creator_user):
    user, ws = test_creator_user
    # Ensure Instagram account is connected
    account = db_session.query(InstagramAccount).filter(InstagramAccount.workspace_id == ws.id).first()
    account.is_connected = True
    db_session.commit()

    # Create signed_request for deauthorize
    payload_data = {
        "user_id": account.ig_user_id,
        "algorithm": "HMAC-SHA256",
        "issued_at": int(time.time())
    }
    payload_json = json.dumps(payload_data, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8").rstrip("=")
    sig = hmac.new(settings.META_APP_SECRET.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")
    signed_request = f"{sig_b64}.{payload_b64}"

    # 1. Invalid signature should return 401
    bad_req = client.post("/api/v1/instagram/deauthorize", data={"signed_request": "bad_sig.bad_payload"})
    assert bad_req.status_code == 401

    # 2. Valid signed request disconnects the account
    good_req = client.post("/api/v1/instagram/deauthorize", data={"signed_request": signed_request})
    assert good_req.status_code == 200
    assert good_req.json()["status"] == "DEAUTHORIZED"

    db_session.refresh(account)
    assert account.is_connected is False
    assert account.encrypted_access_token == ""

def test_meta_data_deletion_callback(client, db_session, test_creator_user):
    user, ws = test_creator_user
    account = db_session.query(InstagramAccount).filter(InstagramAccount.workspace_id == ws.id).first()

    payload_data = {
        "user_id": account.ig_user_id,
        "algorithm": "HMAC-SHA256",
        "issued_at": int(time.time())
    }
    payload_json = json.dumps(payload_data, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8").rstrip("=")
    sig = hmac.new(settings.META_APP_SECRET.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")
    signed_request = f"{sig_b64}.{payload_b64}"

    res = client.post("/api/v1/instagram/data-deletion", data={"signed_request": signed_request})
    assert res.status_code == 200
    res_data = res.json()
    assert "url" in res_data
    assert "confirmation_code" in res_data
    assert res_data["confirmation_code"].startswith("woka_del_")


def test_explicit_account_disconnect(client, auth_headers, db_session):
    account = db_session.query(InstagramAccount).first()
    account.is_connected = True
    db_session.commit()

    res = client.post("/api/v1/instagram/disconnect", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "DISCONNECTED"

    db_session.refresh(account)
    assert account.is_connected is False


def test_staging_health_and_readiness_probes(client):
    """Verifies standard container liveness and database-connected readiness probes."""
    live = client.get("/healthz")
    assert live.status_code == 200
    assert live.json()["status"] == "alive"

    ready = client.get("/readyz")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert ready.json()["database"] == "connected"


def test_staging_rate_limiting_burst_protection(client, auth_headers):
    """Ensures sliding-window rate limiting triggers 429 when max_requests is exceeded."""
    from app.security import reset_rate_limits
    reset_rate_limits()

    # /api/v1/instagram/oauth-url is limited to 15 requests / 60 seconds
    for _ in range(15):
        resp = client.get("/api/v1/instagram/oauth-url", headers=auth_headers)
        assert resp.status_code == 200

    # 16th call must be blocked with HTTP 429 and Retry-After header
    blocked_resp = client.get("/api/v1/instagram/oauth-url", headers=auth_headers)
    assert blocked_resp.status_code == 429
    assert "Rate limit exceeded" in blocked_resp.json()["detail"]
    assert "retry-after" in blocked_resp.headers
    assert int(blocked_resp.headers["retry-after"]) > 0

    reset_rate_limits()


def test_staging_live_vs_sandbox_labeling(client, auth_headers, db_session, test_creator_user):
    """Verifies that sandbox simulation mode is clearly labeled and distinguished from live."""
    user, ws = test_creator_user
    account = db_session.query(InstagramAccount).filter(InstagramAccount.workspace_id == ws.id).first()
    
    # 1. Sandbox mode: is_sandbox=True, mode in provenance
    account.is_connected = True
    account.is_sandbox = True
    db_session.commit()

    status_res = client.get("/api/v1/instagram/status", headers=auth_headers)
    assert status_res.status_code == 200
    assert status_res.json()["account"]["is_sandbox"] is True

    sync_res = client.post("/api/v1/instagram/sync-insights", headers=auth_headers)
    assert sync_res.status_code == 200
    assert sync_res.json()["provenance"]["mode"] == "SANDBOX_SIMULATION"


def test_staging_ssrf_and_dns_rebinding_protection(client, auth_headers):
    """Verifies that private IP and cloud metadata URLs are rejected before network calls."""
    restricted_urls = [
        "https://169.254.169.254/latest/meta-data/",
        "http://127.0.0.1:8000/internal-admin",
        "http://localhost:5432/",
        "http://10.0.0.1/admin",
        "http://192.168.1.1/router"
    ]
    for url in restricted_urls:
        resp = client.post("/api/v1/reel-intelligence/jobs/url", json={"url": url}, headers=auth_headers)
        assert resp.status_code == 422
        assert "private" in resp.json()["detail"].lower() or "restricted" in resp.json()["detail"].lower() or "invalid" in resp.json()["detail"].lower()


def test_staging_upload_malware_magic_bytes_protection(client, auth_headers):
    """Verifies that executables disguised as MP4 files are rejected via magic bytes inspection."""
    import io
    fake_exe = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00malicious binary content")
    res_fake = client.post(
        "/api/v1/reel-intelligence/jobs/upload",
        files={"file": ("malicious.mp4", fake_exe, "video/mp4")},
        headers=auth_headers
    )
    assert res_fake.status_code == 422
    assert "signature does not match" in res_fake.json()["detail"].lower()


def test_database_url_postgres_normalization():
    """Verifies postgres:// URL prefix from Render is normalized to postgresql:// for SQLAlchemy."""
    from app.config import Settings
    custom_settings = Settings(DATABASE_URL="postgres://user:pass@host.render.internal:5432/woka_staging")
    assert custom_settings.DATABASE_URL.startswith("postgresql://")
    assert custom_settings.DATABASE_URL == "postgresql://user:pass@host.render.internal:5432/woka_staging"


def test_cors_origins_and_frontend_url_auto_whitelist():
    """Verifies comma-separated CORS origins and auto-whitelisting of FRONTEND_URL."""
    from app.config import Settings
    custom = Settings(
        CORS_ORIGINS="https://woka-staging.vercel.app, https://staging.woka.io",
        FRONTEND_URL="https://preview-123.vercel.app"
    )
    assert "https://woka-staging.vercel.app" in custom.CORS_ORIGINS
    assert "https://staging.woka.io" in custom.CORS_ORIGINS
    # FRONTEND_URL must be automatically added
    assert "https://preview-123.vercel.app" in custom.CORS_ORIGINS


def test_oauth_connect_with_explicit_redirect_uri(client, auth_headers, test_creator_user):
    """Verifies /api/v1/instagram/connect accepts and processes optional redirect_uri."""
    user, ws = test_creator_user
    state = generate_oauth_state(ws.id)
    res = client.post("/api/v1/instagram/connect", json={
        "code": "mock_code_123",
        "state": state,
        "redirect_uri": "https://woka-staging.vercel.app/dashboard/instagram/callback"
    }, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["is_connected"] is True
