import urllib.parse
import pytest
from app.config import Settings, settings
from app.services.instagram_service import get_oauth_authorization_url


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
