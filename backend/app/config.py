import os
import urllib.parse
from typing import List, Any, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator, field_validator

def validate_and_normalize_redirect_uri(raw_uri: str, api_v1_str: str = "/api/v1") -> str:
    """
    Validates and normalizes an OAuth callback URI.
    Enforces:
    - Non-empty string
    - Well-formed HTTP/HTTPS URL
    - HTTPS required for non-localhost/non-loopback domains
    - Rejects credentials (user:pass@host)
    - Rejects fragments (#...)
    - Rejects query parameters (?...)
    - Path must end with {api_v1_str}/instagram/callback
    Returns strictly normalized canonical URL with no trailing slash.
    """
    if not raw_uri or not isinstance(raw_uri, str):
        raise ValueError("CRITICAL CONFIGURATION ERROR: OAuth callback URI cannot be empty.")

    clean_uri = raw_uri.strip().rstrip("/")
    parsed = urllib.parse.urlparse(clean_uri)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"CRITICAL CONFIGURATION ERROR: Invalid OAuth callback URI scheme '{parsed.scheme}'. "
            "Must be 'http' (localhost only) or 'https'."
        )

    if not parsed.netloc or not parsed.hostname:
        raise ValueError(
            f"CRITICAL CONFIGURATION ERROR: Malformed OAuth callback URI '{raw_uri}'. Missing valid host."
        )

    if parsed.username or parsed.password:
        raise ValueError(
            "CRITICAL SECURITY VIOLATION: OAuth callback URI must not contain embedded user credentials."
        )

    if parsed.fragment:
        raise ValueError(
            "CRITICAL SECURITY VIOLATION: OAuth callback URI must not contain URL fragments (#)."
        )

    if parsed.query:
        raise ValueError(
            "CRITICAL SECURITY VIOLATION: OAuth callback URI must not contain query parameters (?)."
        )

    hostname_lower = (parsed.hostname or "").lower()
    is_local = hostname_lower in ("localhost", "127.0.0.1", "testserver")
    if not is_local and parsed.scheme != "https":
        raise ValueError(
            f"CRITICAL SECURITY VIOLATION: Public OAuth callback domain '{parsed.hostname}' must use HTTPS."
        )

    expected_path = f"{api_v1_str.rstrip('/')}/instagram/callback"
    normalized_path = parsed.path.rstrip("/")
    if normalized_path != expected_path:
        raise ValueError(
            f"CRITICAL CONFIGURATION ERROR: OAuth callback URI '{clean_uri}' path '{normalized_path}' "
            f"does not match exact canonical backend callback path '{expected_path}'."
        )

    return f"{parsed.scheme}://{parsed.netloc}{normalized_path}"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Woka API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security & JWT
    SECRET_KEY: str = Field(default="woka-super-secret-production-grade-signing-key-32chars-min!", description="JWT signing key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # Fernet AES-256 Symmetric key for token encryption at rest (url-safe base64 32-bytes)
    TOKEN_ENCRYPTION_KEY: str = Field(
        default="eF9rVlBfZkRzQ3ZfU0VDUkVUX0tFWV8xMjM0NTY3ODk=",
        description="Fernet 32-byte urlsafe key for encrypting Meta OAuth tokens at rest"
    )

    # Database
    DATABASE_URL: str = Field(default="sqlite:///./woka.db", description="SQLAlchemy database URL")

    # Redis (Cache, Sliding-Window Rate Limiting, Background Workers)
    REDIS_URL: str = Field(
        default="",
        description="Redis connection URL for shared caching and background processing"
    )

    # Official Meta / Instagram App Credentials & Endpoints
    META_APP_ID: str = Field(default="mock_meta_app_id_12345", description="Meta Developer App ID")
    META_APP_SECRET: str = Field(default="mock_meta_app_secret_67890", description="Meta Developer App Secret")
    META_CLIENT_SECRET: Optional[str] = Field(default=None, description="Documented alias for META_APP_SECRET")
    META_VERIFY_TOKEN: str = Field(default="woka_meta_webhook_verify_token_2026", description="Webhook handshake token")
    META_REDIRECT_URI: str = Field(default="", description="Canonical OAuth callback URI")
    META_API_VERSION: str = Field(default="v21.0", description="Meta Graph API version (e.g. v21.0)")
    INSTAGRAM_GRAPH_HOST: str = Field(default="https://graph.instagram.com", description="Instagram Graph API host")
    INSTAGRAM_LOGIN_HOST: str = Field(default="https://api.instagram.com", description="Instagram OAuth API host")
    INSTAGRAM_AUTH_HOST: str = Field(default="https://www.instagram.com", description="Instagram Web Authorize host")
    FRONTEND_URL: str = Field(default="http://localhost:3000", description="Frontend application URL")

    # Public Backend URL (used when exposed via ngrok or cloud domain)
    BACKEND_PUBLIC_URL: str = Field(
        default="",
        description="Public backend HTTPS URL when exposed via ngrok or cloud host (e.g. https://your-domain.ngrok-free.app)"
    )

    # CORS & Trusted Hosts
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://woka-reel-intelligence.vercel.app"
    ]
    ALLOWED_HOSTS: List[str] = Field(
        default=["*"],
        description="Allowed host headers for TrustedHostMiddleware"
    )

    # Test & Sandbox Controls
    ENABLE_MOCK_OAUTH: bool = Field(
        default=False,
        description="Explicit test-mode setting allowing mock/synthetic OAuth authorization codes. Strictly forbidden in production."
    )

    # Optional AI Provider (if empty, Woka's intelligent local template & NLP heuristic engine is used)
    OPENAI_API_KEY: str = Field(default="", description="Optional OpenAI API Key")

    model_config = SettingsConfigDict(
        env_file=(
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
            ".env",
            "backend/.env"
        ),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_str = v.strip()
            # Normalize postgres:// to postgresql:// for SQLAlchemy compatibility on Render/Fly/Neon
            if v_str.startswith("postgres://"):
                return v_str.replace("postgres://", "postgresql://", 1)
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("[") and v_str.endswith("]"):
                import json
                try:
                    return json.loads(v_str)
                except Exception:
                    pass
            return [origin.strip() for origin in v_str.split(",") if origin.strip()]
        return v

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("[") and v_str.endswith("]"):
                import json
                try:
                    return json.loads(v_str)
                except Exception:
                    pass
            return [host.strip() for host in v_str.split(",") if host.strip()]
        return v

    @property
    def effective_instagram_redirect_uri(self) -> str:
        """
        Single canonical source of truth for the Meta Instagram OAuth callback URI.
        Requires BACKEND_PUBLIC_URL or an explicitly configured META_REDIRECT_URI.
        Never silently falls back to FRONTEND_URL.
        Validates URL structure, schemes, host, credentials, fragments, query strings, and path.
        """
        raw_uri = ""
        if self.BACKEND_PUBLIC_URL:
            base = self.BACKEND_PUBLIC_URL.strip().rstrip("/")
            raw_uri = f"{base}{self.API_V1_STR}/instagram/callback"
        elif self.META_REDIRECT_URI:
            raw_uri = self.META_REDIRECT_URI.strip().rstrip("/")
        else:
            raise ValueError(
                "CRITICAL CONFIGURATION ERROR: Neither BACKEND_PUBLIC_URL nor an explicit META_REDIRECT_URI "
                "is configured. A backend public URL or canonical OAuth callback URI is required."
            )

        return validate_and_normalize_redirect_uri(raw_uri, api_v1_str=self.API_V1_STR)

    @property
    def public_oauth_callback_url(self) -> str:
        return self.effective_instagram_redirect_uri

    @property
    def meta_client_secret(self) -> str:
        """Documented alias for META_APP_SECRET."""
        return self.META_APP_SECRET

    @property
    def public_webhook_url(self) -> str:
        base = self.BACKEND_PUBLIC_URL.strip().rstrip('/') if self.BACKEND_PUBLIC_URL else "http://localhost:8000"
        return f"{base}{self.API_V1_STR}/instagram/webhook"

    @property
    def public_deauthorize_url(self) -> str:
        base = self.BACKEND_PUBLIC_URL.strip().rstrip('/') if self.BACKEND_PUBLIC_URL else "http://localhost:8000"
        return f"{base}{self.API_V1_STR}/instagram/deauthorize"

    @property
    def public_data_deletion_url(self) -> str:
        base = self.BACKEND_PUBLIC_URL.strip().rstrip('/') if self.BACKEND_PUBLIC_URL else "http://localhost:8000"
        return f"{base}{self.API_V1_STR}/instagram/data-deletion"

    @model_validator(mode="after")
    def validate_production_security(self):
        # Auto-include FRONTEND_URL in CORS_ORIGINS to prevent cross-origin mismatches
        if self.FRONTEND_URL:
            self.FRONTEND_URL = self.FRONTEND_URL.strip().rstrip("/")
            if self.FRONTEND_URL not in self.CORS_ORIGINS:
                self.CORS_ORIGINS.append(self.FRONTEND_URL)

        if self.META_CLIENT_SECRET:
            self.META_APP_SECRET = self.META_CLIENT_SECRET

        # Dynamic ngrok / public URL handling & Callback URI Validation
        if self.BACKEND_PUBLIC_URL:
            clean_public = self.BACKEND_PUBLIC_URL.strip().rstrip('/')
            if clean_public:
                parsed_base = urllib.parse.urlparse(clean_public)
                if parsed_base.scheme not in ("http", "https"):
                    raise ValueError(f"CRITICAL CONFIGURATION ERROR: BACKEND_PUBLIC_URL must start with http:// or https:// (got: {clean_public})")
                is_local = (parsed_base.hostname or "").lower() in ("localhost", "127.0.0.1", "testserver")
                if not is_local and parsed_base.scheme != "https":
                    raise ValueError(f"CRITICAL CONFIGURATION ERROR: BACKEND_PUBLIC_URL must use HTTPS for public domains (got: {clean_public})")

                self.BACKEND_PUBLIC_URL = clean_public
                # Single canonical synchronization & strict validation
                canonical_uri = f"{clean_public}{self.API_V1_STR}/instagram/callback"
                self.META_REDIRECT_URI = validate_and_normalize_redirect_uri(canonical_uri, api_v1_str=self.API_V1_STR)

                if clean_public not in self.CORS_ORIGINS:
                    self.CORS_ORIGINS.append(clean_public)
                host = parsed_base.netloc
                if host and "*" not in self.ALLOWED_HOSTS and host not in self.ALLOWED_HOSTS:
                    self.ALLOWED_HOSTS.append(host)
        else:
            if self.META_REDIRECT_URI:
                clean_redirect = self.META_REDIRECT_URI.strip().rstrip("/")
                self.META_REDIRECT_URI = validate_and_normalize_redirect_uri(clean_redirect, api_v1_str=self.API_V1_STR)

        if self.ENVIRONMENT.lower() == "production":
            default_secret = "woka-super-secret-production-grade-signing-key-32chars-min!"
            default_fernet = "eF9rVlBfZkRzQ3ZfU0VDUkVUX0tFWV8xMjM0NTY3ODk="
            if self.SECRET_KEY == default_secret:
                raise ValueError("CRITICAL SECURITY VIOLATION: Default SECRET_KEY cannot be used in production environment.")
            if self.TOKEN_ENCRYPTION_KEY == default_fernet:
                raise ValueError("CRITICAL SECURITY VIOLATION: Default TOKEN_ENCRYPTION_KEY cannot be used in production environment.")
            if not self.META_APP_ID or self.META_APP_ID.startswith("mock_"):
                raise ValueError("CRITICAL CONFIGURATION ERROR: Valid META_APP_ID must be configured for production.")
            if not self.META_APP_SECRET or self.META_APP_SECRET.startswith("mock_"):
                raise ValueError("CRITICAL CONFIGURATION ERROR: Valid META_APP_SECRET must be configured for production.")
            if not self.META_REDIRECT_URI or "localhost" in self.META_REDIRECT_URI:
                raise ValueError("CRITICAL CONFIGURATION ERROR: Valid META_REDIRECT_URI must be configured for production.")
            if self.ENABLE_MOCK_OAUTH:
                raise ValueError("CRITICAL SECURITY VIOLATION: ENABLE_MOCK_OAUTH cannot be true in production environment.")
        return self

settings = Settings()
