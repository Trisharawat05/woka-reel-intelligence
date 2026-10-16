import pytest
from app.security import create_refresh_token

def test_refresh_token_cannot_access_protected_endpoint(client, test_creator_user):
    user, ws = test_creator_user
    # Issue a refresh token
    refresh_tok = create_refresh_token(data={"sub": user.id})

    # Attempt to use refresh token as Bearer access token
    headers = {"Authorization": f"Bearer {refresh_tok}"}
    res = client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 401
    assert "access token required" in res.json()["detail"].lower()

def test_refresh_token_flow_and_rotation(client):
    # Register a new user
    reg_payload = {
        "email": "refresher@woka.io",
        "password": "Password123!",
        "full_name": "Token Refresher",
        "role": "CREATOR"
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    old_refresh = reg_res.json()["refresh_token"]

    # Exchange refresh token for a new pair
    ref_res = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert ref_res.status_code == 200
    ref_data = ref_res.json()
    new_access = ref_data["access_token"]
    new_refresh = ref_data["refresh_token"]

    assert new_access is not None
    assert new_refresh is not None
    assert new_refresh != old_refresh

    # Validate that new access token can access /me
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me_res.status_code == 200
    assert me_res.json()["user"]["email"] == "refresher@woka.io"

    # Verify old refresh token is revoked and cannot be reused
    reused_res = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reused_res.status_code == 401
    assert "revoked" in reused_res.json()["detail"].lower()

def test_logout_revocation(client):
    login_user = {
        "email": "logout_user@woka.io",
        "password": "Password123!",
        "full_name": "Logout Tester",
        "role": "CREATOR"
    }
    reg_res = client.post("/api/v1/auth/register", json=login_user)
    assert reg_res.status_code == 201
    access_tok = reg_res.json()["access_token"]
    refresh_tok = reg_res.json()["refresh_token"]

    headers = {"Authorization": f"Bearer {access_tok}"}
    # Verify access works before logout
    before_res = client.get("/api/v1/auth/me", headers=headers)
    assert before_res.status_code == 200

    # Logout and revoke both tokens
    logout_res = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_tok}, headers=headers)
    assert logout_res.status_code == 200
    assert "revoked" in logout_res.json()["message"].lower()

    # Access token must now be rejected
    after_res = client.get("/api/v1/auth/me", headers=headers)
    assert after_res.status_code == 401
    assert "revoked" in after_res.json()["detail"].lower()

    # Refresh token must also be rejected
    refresh_attempt = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_tok})
    assert refresh_attempt.status_code == 401
    assert "revoked" in refresh_attempt.json()["detail"].lower()
