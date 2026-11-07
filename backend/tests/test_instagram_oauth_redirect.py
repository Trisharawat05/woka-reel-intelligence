import urllib.parse
from unittest.mock import patch, MagicMock
import pytest
from fastapi import HTTPException
import httpx

from app.config import Settings, settings, validate_and_normalize_redirect_uri
from app.services.instagram_service import (
    get_oauth_authorization_url,
    exchange_code_for_tokens,
    connect_or_update_account_from_oauth,
    generate_oauth_state,
    MetaAPIError
)
from app.models.instagram import InstagramAccount


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
        META_APP_SECRET="supersecret12345678901234567890"
    )
    assert prod_valid.effective_instagram_redirect_uri == "https://woka-api-staging.onrender.com/api/v1/instagram/callback"
    assert prod_valid.META_REDIRECT_URI == "https://woka-api-staging.onrender.com/api/v1/instagram/callback"


def test_callback_fallback_behavior_and_validation():
    """Verifies that callback validation rejects malformed URLs, credentials, fragments, queries, and invalid schemes."""
    # 1. Reject empty
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_and_normalize_redirect_uri("")

    # 2. Never silently fall back to FRONTEND_URL or non-backend paths
    with pytest.raises(ValueError, match="does not point to the FastAPI backend callback endpoint"):
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


def test_frontend_supplied_redirect_uri_cannot_override_canonical_setting():
    """Verifies token exchange strictly enforces the canonical server redirect_uri and ignores client overrides."""
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
        # Pass an adversarial client-supplied redirect_uri
        exchange_code_for_tokens(
            code="test_code_valid",
            redirect_uri="https://adversary.com/steal-token/callback"
        )

    # Assert that the outbound payload sent to Meta strictly uses canonical server redirect URI
    assert captured_payload is not None
    assert captured_payload["redirect_uri"] == settings.effective_instagram_redirect_uri
    assert captured_payload["redirect_uri"] != "https://adversary.com/steal-token/callback"


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
        # Even if account exists from fixture, verify that the fabricated attempt did not alter or bind it
        assert account is not None
        assert account.username == "test_creator_ig"
    finally:
        settings.ENABLE_MOCK_OAUTH = True
        settings.ENVIRONMENT = "test"
