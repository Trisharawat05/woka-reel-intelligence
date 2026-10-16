from app.config import settings
from app.security import encrypt_token, decrypt_token

def test_meta_webhook_challenge_success(client):
    res = client.get(
        "/api/v1/instagram/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "challenge_code_987654",
            "hub.verify_token": settings.META_VERIFY_TOKEN
        }
    )
    assert res.status_code == 200
    assert res.text == "challenge_code_987654"

def test_meta_webhook_challenge_invalid_token(client):
    res = client.get(
        "/api/v1/instagram/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "challenge_code_987654",
            "hub.verify_token": "wrong_unauthorized_token"
        }
    )
    assert res.status_code == 403

def test_token_encryption_roundtrip():
    secret_token = "EAABwzLixnjYBAK...sensitive_oauth_token"
    encrypted = encrypt_token(secret_token)
    assert encrypted != secret_token
    assert len(encrypted) > 20
    decrypted = decrypt_token(encrypted)
    assert decrypted == secret_token

def test_instagram_sandbox_toggle(client, auth_headers):
    # Toggle off
    res = client.post("/api/v1/instagram/sandbox/toggle", json={"enabled": False}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["is_connected"] is False

    # Toggle back on
    res2 = client.post("/api/v1/instagram/sandbox/toggle", json={
        "enabled": True,
        "username": "custom_demo_creator",
        "followers_count": 52000
    }, headers=auth_headers)
    assert res2.status_code == 200
    data = res2.json()
    assert data["is_connected"] is True
    assert data["is_sandbox"] is True
    assert data["username"] == "custom_demo_creator"
    assert data["followers_count"] == 52000
