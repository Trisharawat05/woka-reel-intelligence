import os
from typing import List, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator, field_validator

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

    # Official Meta / Instagram App Credentials
    META_APP_ID: str = Field(default="mock_meta_app_id_12345", description="Meta Developer App ID")
    META_APP_SECRET: str = Field(default="mock_meta_app_secret_67890", description="Meta Developer App Secret")
    META_VERIFY_TOKEN: str = Field(default="woka_meta_webhook_verify_token_2026", description="Webhook handshake token")
    META_REDIRECT_URI: str = Field(default="http://localhost:3000/dashboard/instagram/callback", description="OAuth callback URI")
    META_API_VERSION: str = Field(default="v21.0", description="Meta Graph API version (e.g. v21.0)")
    FRONTEND_URL: str = Field(default="http://localhost:3000", description="Frontend application URL")

    # CORS & Trusted Hosts
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]
    ALLOWED_HOSTS: List[str] = Field(
        default=["*"],
        description="Allowed host headers for TrustedHostMiddleware"
    )

    # Optional AI Provider (if empty, Woka's intelligent local template & NLP heuristic engine is used)
    OPENAI_API_KEY: str = Field(default="", description="Optional OpenAI API Key")

    model_config = SettingsConfigDict(
        env_file=".env",
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

    @model_validator(mode="after")
    def validate_production_security(self):
        # Auto-include FRONTEND_URL in CORS_ORIGINS to prevent cross-origin mismatches
        if self.FRONTEND_URL and self.FRONTEND_URL not in self.CORS_ORIGINS:
            self.CORS_ORIGINS.append(self.FRONTEND_URL)

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
        return self

settings = Settings()
