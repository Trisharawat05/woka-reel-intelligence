import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator

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
    # Default development key provided for zero-friction local run; override via environment variable in production
    TOKEN_ENCRYPTION_KEY: str = Field(
        default="eF9rVlBfZkRzQ3ZfU0VDUkVUX0tFWV8xMjM0NTY3ODk=",
        description="Fernet 32-byte urlsafe key for encrypting Meta OAuth tokens at rest"
    )

    # Database
    DATABASE_URL: str = Field(default="sqlite:///./woka.db", description="SQLAlchemy database URL")

    # Official Meta / Instagram App Credentials
    META_APP_ID: str = Field(default="mock_meta_app_id_12345", description="Meta Developer App ID")
    META_APP_SECRET: str = Field(default="mock_meta_app_secret_67890", description="Meta Developer App Secret")
    META_VERIFY_TOKEN: str = Field(default="woka_meta_webhook_verify_token_2026", description="Webhook handshake token")
    META_REDIRECT_URI: str = Field(default="http://localhost:3000/dashboard/instagram/callback", description="OAuth callback URI")
    META_API_VERSION: str = Field(default="v21.0", description="Meta Graph API version (e.g. v21.0)")
    FRONTEND_URL: str = Field(default="http://localhost:3000", description="Frontend application URL")

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

    # Optional AI Provider (if empty, Woka's intelligent local template & NLP heuristic engine is used)
    OPENAI_API_KEY: str = Field(default="", description="Optional OpenAI API Key")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @model_validator(mode="after")
    def validate_production_security(self):
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
