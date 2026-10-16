import json
import hmac
import hashlib
from app.config import settings
from app.services.instagram_service import generate_oauth_state

def test_oauth_state_csrf_protection(client, auth_headers):
    # 1. Attempt connection with forged / unsigned state parameter -> 400 Bad Request
    tampered_state = "eyJ3b3Jrc3BhY2VfaWQiOiIxMjM0NSJ9.invalid_signature_hash"
    bad_res = client.post("/api/v1/instagram/connect", json={
        "code": "auth_code_123",
        "state": tampered_state
    }, headers=auth_headers)
    assert bad_res.status_code == 400
    assert "csrf protection failed" in bad_res.json()["detail"].lower()

    # 2. Get valid signed state from /oauth-url
    oauth_res = client.get("/api/v1/instagram/oauth-url", headers=auth_headers)
    assert oauth_res.status_code == 200
    valid_state = oauth_res.json()["state"]

    # 3. Connection with valid signed state -> 200 OK
    good_res = client.post("/api/v1/instagram/connect", json={
        "code": "auth_code_123",
        "state": valid_state
    }, headers=auth_headers)
    assert good_res.status_code == 200
    assert good_res.json()["is_connected"] is True

def test_webhook_event_processing_and_idempotency(client, auth_headers):
    # Create automation
    auto_res = client.post("/api/v1/automations", json={
        "name": "Course Link",
        "trigger_type": "COMMENT",
        "target_post_type": "ALL_POSTS",
        "match_type": "CONTAINS_ANY",
        "trigger_keywords": ["course", "learn"],
        "dm_message_template": "Hey {{username}}, here is the course link: https://woka.io/learn",
        "is_active": True,
        "cooldown_minutes": 60
    }, headers=auth_headers)
    assert auto_res.status_code == 201

    webhook_payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "ig_test_user_id",
                "time": 1729000000,
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "id": "webhook_comment_unique_999",
                            "text": "How do I join the course?",
                            "from": {
                                "id": "student_fan_101",
                                "username": "student_fan"
                            },
                            "media": {
                                "id": "reel_post_555"
                            }
                        }
                    }
                ]
            }
        ]
    }
    raw_bytes = json.dumps(webhook_payload).encode()
    signature = "sha256=" + hmac.new(settings.META_APP_SECRET.encode(), raw_bytes, hashlib.sha256).hexdigest()

    # 1. First webhook delivery
    res1 = client.post(
        "/api/v1/instagram/webhook",
        content=raw_bytes,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": signature}
    )
    assert res1.status_code == 200
    res1_data = res1.json()
    assert res1_data["status"] == "PROCESSED"
    assert len(res1_data["results"]) == 1
    assert res1_data["results"][0]["status"] in ["SUCCESS", "SIMULATED"]
    assert res1_data["results"][0]["recipient"] == "student_fan"

    # 2. Duplicate webhook delivery with identical comment ID -> must be ignored (idempotent)
    res2 = client.post(
        "/api/v1/instagram/webhook",
        content=raw_bytes,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": signature}
    )
    assert res2.status_code == 200
    res2_data = res2.json()
    assert res2_data["results"][0]["status"] == "DUPLICATE_IGNORED"

def test_webhook_anti_spam_cooldown(client, auth_headers):
    # Create automation with 60-minute cooldown
    client.post("/api/v1/automations", json={
        "name": "VIP Discount",
        "trigger_type": "COMMENT",
        "target_post_type": "ALL_POSTS",
        "match_type": "CONTAINS_ANY",
        "trigger_keywords": ["vip", "code"],
        "dm_message_template": "VIP code for you {{username}}: VIP100",
        "is_active": True,
        "cooldown_minutes": 60
    }, headers=auth_headers)

    # First comment from rapid_user
    payload1 = {
        "object": "instagram",
        "entry": [{
            "id": "ig_test_user_id",
            "changes": [{
                "field": "comments",
                "value": {
                    "id": "rapid_comment_001",
                    "text": "Send me the vip code please!",
                    "from": {"id": "rapid_user_id", "username": "rapid_user"}
                }
            }]
        }]
    }
    raw1 = json.dumps(payload1).encode()
    sig1 = "sha256=" + hmac.new(settings.META_APP_SECRET.encode(), raw1, hashlib.sha256).hexdigest()

    res1 = client.post("/api/v1/instagram/webhook", content=raw1, headers={"X-Hub-Signature-256": sig1})
    assert res1.status_code == 200
    assert res1.json()["results"][0]["status"] in ["SUCCESS", "SIMULATED"]

    # Second comment within minutes from same author with different comment ID
    payload2 = {
        "object": "instagram",
        "entry": [{
            "id": "ig_test_user_id",
            "changes": [{
                "field": "comments",
                "value": {
                    "id": "rapid_comment_002",
                    "text": "VIP code again please!",
                    "from": {"id": "rapid_user_id", "username": "rapid_user"}
                }
            }]
        }]
    }
    raw2 = json.dumps(payload2).encode()
    sig2 = "sha256=" + hmac.new(settings.META_APP_SECRET.encode(), raw2, hashlib.sha256).hexdigest()

    res2 = client.post("/api/v1/instagram/webhook", content=raw2, headers={"X-Hub-Signature-256": sig2})
    assert res2.status_code == 200
    assert res2.json()["results"][0]["status"] == "SUPPRESSED_COOLDOWN"
