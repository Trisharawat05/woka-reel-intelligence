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
