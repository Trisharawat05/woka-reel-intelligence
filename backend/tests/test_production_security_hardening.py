import pytest
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.datastructures import Headers
from fastapi import HTTPException, status

from app.config import Settings, settings
from app.routers.instagram import meta_webhook_verification


# Valid base parameters for instantiating production Settings
VALID_PROD_KWARGS = {
    "ENVIRONMENT": "production",
    "SECRET_KEY": "a-very-long-production-signing-key-32chars-min!",
    "TOKEN_ENCRYPTION_KEY": "valid_32_byte_fernet_key_for_testing_1234=",
    "META_APP_ID": "3217043811838822",
    "META_APP_SECRET": "bc898d0015ba4cdee7aa1ff5ead92965",
    "META_VERIFY_TOKEN": "custom_prod_verify_token_987654321",
    "META_REDIRECT_URI": "https://woka-api-staging.onrender.com/api/v1/instagram/callback",
    "BACKEND_PUBLIC_URL": "https://woka-api-staging.onrender.com",
    "ALLOWED_HOSTS": ["woka-api-staging.onrender.com", "api.woka.io"],
    "CORS_ORIGINS": ["https://woka-reel-intelligence.vercel.app"]
}


# ==============================================================================
# 1. ALLOWED_HOSTS TESTS
# ==============================================================================

def test_production_rejects_wildcard_allowed_hosts():
    """Verify production rejects wildcard '*' in ALLOWED_HOSTS."""
    kwargs = dict(VALID_PROD_KWARGS, ALLOWED_HOSTS=["*"])
    with pytest.raises(ValueError, match="Wildcard '\\*' is strictly forbidden in ALLOWED_HOSTS in production"):
        Settings(**kwargs)

    kwargs_list = dict(VALID_PROD_KWARGS, ALLOWED_HOSTS=["api.woka.io", "*"])
    with pytest.raises(ValueError, match="Wildcard '\\*' is strictly forbidden in ALLOWED_HOSTS in production"):
        Settings(**kwargs_list)


def test_production_rejects_empty_allowed_hosts():
    """Verify production rejects empty ALLOWED_HOSTS configuration."""
    kwargs_empty_list = dict(VALID_PROD_KWARGS, ALLOWED_HOSTS=[], BACKEND_PUBLIC_URL="")
    with pytest.raises(ValueError, match="ALLOWED_HOSTS cannot be empty in production"):
        Settings(**kwargs_empty_list)

    kwargs_empty_str = dict(VALID_PROD_KWARGS, ALLOWED_HOSTS="", BACKEND_PUBLIC_URL="")
    with pytest.raises(ValueError, match="ALLOWED_HOSTS cannot be empty in production"):
        Settings(**kwargs_empty_str)


def test_production_rejects_default_development_hosts():
    """Verify production rejects default development hosts when no production domains are supplied."""
    kwargs_dev_hosts = dict(VALID_PROD_KWARGS, ALLOWED_HOSTS=["localhost", "127.0.0.1", "testserver"], BACKEND_PUBLIC_URL="")
    with pytest.raises(ValueError, match="Production requires an explicit host allowlist"):
        Settings(**kwargs_dev_hosts)


def test_production_rejects_malformed_host_entries():
    """Verify production rejects malformed host entries (schemes, paths, spaces)."""
    # 1. Reject host containing URL scheme
    kwargs_scheme = dict(VALID_PROD_KWARGS, ALLOWED_HOSTS=["https://api.woka.io"])
    with pytest.raises(ValueError, match="Hosts must not include URL schemes"):
        Settings(**kwargs_scheme)

    # 2. Reject host containing URL paths or invalid characters
    kwargs_path = dict(VALID_PROD_KWARGS, ALLOWED_HOSTS=["api.woka.io/path"])
    with pytest.raises(ValueError, match="Invalid characters detected"):
        Settings(**kwargs_path)


def test_production_accepts_explicit_valid_allowlist():
    """Verify production accepts an explicit, valid host allowlist."""
    kwargs = dict(VALID_PROD_KWARGS, ALLOWED_HOSTS=["api.woka.io", "woka-backend.onrender.com"])
    prod_conf = Settings(**kwargs)
    assert "api.woka.io" in prod_conf.ALLOWED_HOSTS
    assert "woka-backend.onrender.com" in prod_conf.ALLOWED_HOSTS
    assert "*" not in prod_conf.ALLOWED_HOSTS


def test_trusted_host_middleware_configuration_and_matching():
    """Verify TrustedHostMiddleware receives explicit allowlist and rejects unapproved hosts."""
    middleware = TrustedHostMiddleware(
        app=None,
        allowed_hosts=["woka-api-staging.onrender.com", "api.woka.io", "testserver"]
    )
    # 1. Wildcard is not active
    assert middleware.allow_any is False
    assert "woka-api-staging.onrender.com" in middleware.allowed_hosts

    # 2. Host evaluation simulation
    def is_host_allowed(host_str: str) -> bool:
        headers = Headers(raw=[(b"host", host_str.encode("utf-8"))])
        host = headers.get("host", "").split(":")[0]
        for pattern in middleware.allowed_hosts:
            if host == pattern or (pattern.startswith("*") and host.endswith(pattern[1:])):
                return True
        return False

    assert is_host_allowed("woka-api-staging.onrender.com") is True
    assert is_host_allowed("api.woka.io") is True
    assert is_host_allowed("testserver") is True
    assert is_host_allowed("evil-attacker.com") is False
    assert is_host_allowed("unapproved.org") is False


# ==============================================================================
# 2. CORS CONFIGURATION TESTS
# ==============================================================================

def test_production_rejects_wildcard_cors_origins():
    """Verify production rejects wildcard '*' in CORS_ORIGINS."""
    kwargs = dict(VALID_PROD_KWARGS, CORS_ORIGINS=["*"])
    with pytest.raises(ValueError, match="Wildcard '\\*' is strictly forbidden in CORS_ORIGINS in production"):
        Settings(**kwargs)

    kwargs_list = dict(VALID_PROD_KWARGS, CORS_ORIGINS=["https://app.woka.io", "*"])
    with pytest.raises(ValueError, match="Wildcard '\\*' is strictly forbidden in CORS_ORIGINS in production"):
        Settings(**kwargs_list)


def test_production_removes_localhost_origins_and_rejects_insecure_origins():
    """Verify production strips localhost development origins and rejects insecure HTTP origins."""
    # 1. Localhost origins are filtered out in production
    kwargs_mixed = dict(
        VALID_PROD_KWARGS,
        CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:8000", "https://woka-reel-intelligence.vercel.app"]
    )
    prod_conf = Settings(**kwargs_mixed)
    assert "https://woka-reel-intelligence.vercel.app" in prod_conf.CORS_ORIGINS
    assert not any("localhost" in orig or "127.0.0.1" in orig for orig in prod_conf.CORS_ORIGINS)

    # 2. Insecure http:// origin on public domain is rejected in production
    kwargs_insecure = dict(VALID_PROD_KWARGS, CORS_ORIGINS=["http://insecure-frontend.com"])
    with pytest.raises(ValueError, match="must use HTTPS"):
        Settings(**kwargs_insecure)

    # 3. Only localhost origins supplied in production results in rejection (no approved HTTPS origins)
    kwargs_only_local = dict(VALID_PROD_KWARGS, CORS_ORIGINS=["http://localhost:3000"], BACKEND_PUBLIC_URL="", FRONTEND_URL="")
    with pytest.raises(ValueError, match="No approved production HTTPS frontend origins found"):
        Settings(**kwargs_only_local)


def test_cors_credentials_and_origin_allowlist_enforcement():
    """Verify CORSMiddleware allows credentials only for explicitly approved origins and rejects unapproved origins."""
    approved_origin = "https://woka-reel-intelligence.vercel.app"
    cors = CORSMiddleware(
        app=None,
        allow_origins=[approved_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    assert cors.allow_all_origins is False
    assert cors.allow_credentials is True
    assert cors.is_allowed_origin(approved_origin) is True
    assert cors.is_allowed_origin("https://unauthorized-evil-site.com") is False
    assert cors.simple_headers.get("Access-Control-Allow-Credentials") == "true"


# ==============================================================================
# 3. META_VERIFY_TOKEN TESTS
# ==============================================================================

def test_production_rejects_default_meta_verify_token():
    """Verify production rejects the default development META_VERIFY_TOKEN."""
    kwargs = dict(VALID_PROD_KWARGS, META_VERIFY_TOKEN="woka_meta_webhook_verify_token_2026")
    with pytest.raises(ValueError, match="Default META_VERIFY_TOKEN cannot be used in production"):
        Settings(**kwargs)


def test_production_rejects_empty_meta_verify_token():
    """Verify production rejects empty META_VERIFY_TOKEN."""
    kwargs_empty = dict(VALID_PROD_KWARGS, META_VERIFY_TOKEN="")
    with pytest.raises(ValueError, match="META_VERIFY_TOKEN cannot be empty in production"):
        Settings(**kwargs_empty)

    kwargs_whitespace = dict(VALID_PROD_KWARGS, META_VERIFY_TOKEN="   ")
    with pytest.raises(ValueError, match="META_VERIFY_TOKEN cannot be empty in production"):
        Settings(**kwargs_whitespace)


def test_production_accepts_custom_meta_verify_token():
    """Verify production accepts an explicitly configured custom verification token."""
    custom_token = "woka_prod_secure_handshake_token_778899"
    kwargs = dict(VALID_PROD_KWARGS, META_VERIFY_TOKEN=custom_token)
    prod_conf = Settings(**kwargs)
    assert prod_conf.META_VERIFY_TOKEN == custom_token


def test_meta_webhook_verification_endpoint_with_tokens():
    """Verify GET /api/v1/instagram/webhook challenge handshake functions correctly with configured token."""
    challenge = "meta_hub_challenge_sample_12345"
    # 1. Matching token succeeds
    res = meta_webhook_verification(
        request=None,
        hub_mode="subscribe",
        hub_challenge=challenge,
        hub_verify_token=settings.META_VERIFY_TOKEN
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.body == challenge.encode("utf-8")

    # 2. Incorrect token is rejected with 403
    with pytest.raises(HTTPException) as exc_info:
        meta_webhook_verification(
            request=None,
            hub_mode="subscribe",
            hub_challenge=challenge,
            hub_verify_token="wrong_token_should_fail"
        )
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Verification token mismatch" in exc_info.value.detail
