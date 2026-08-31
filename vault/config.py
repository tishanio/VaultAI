from __future__ import annotations

"""Application configuration using pydantic-settings."""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Vault application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Application ---
    APP_NAME: str = "Vault"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    DEMO_MODE: bool = True
    SECRET_KEY: str = "change-me-in-production-use-aws-secrets-manager"
    API_PREFIX: str = "/api/v1"

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://vault:vault_secret@localhost:5432/vault_db"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 300

    # --- Authentication ---
    JWT_PRIVATE_KEY_PATH: str = "keys/jwt_private.pem"
    JWT_PUBLIC_KEY_PATH: str = "keys/jwt_public.pem"
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    OAUTH2_CLIENT_ID: str = ""
    OAUTH2_CLIENT_SECRET: str = ""

    # --- Stripe ---
    STRIPE_SECRET_KEY: str = "sk_test_placeholder"
    STRIPE_PUBLISHABLE_KEY: str = "pk_test_placeholder"
    STRIPE_WEBHOOK_SECRET: str = "whsec_placeholder"
    STRIPE_CONNECT_CLIENT_ID: str = ""
    PLATFORM_FEE_PERCENTAGE: float = 12.0

    # --- Razorpay ---
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    RAZORPAY_MODE: str = "sandbox"  # sandbox | live

    # --- Plaid ---
    PLAID_CLIENT_ID: str = ""
    PLAID_SECRET: str = ""
    PLAID_ENV: str = "sandbox"

    # --- Onfido ---
    ONFIDO_API_TOKEN: str = ""
    ONFIDO_WEBHOOK_SECRET: str = ""
    ONFIDO_MOCK_MODE: bool = True

    # --- Notifications ---
    SENDGRID_API_KEY: str = ""
    FCM_CREDENTIALS_PATH: str = ""
    TELEGRAM_BOT_TOKEN: str = ""

    # --- AWS ---
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str = "vault-assets"
    AWS_SECRETS_MANAGER_PREFIX: str = "vault/"

    # --- Encryption ---
    ENCRYPTION_KEY: str = ""  # AES-256-GCM key, base64-encoded

    # --- Celery ---
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # --- Rate Limiting ---
    RATE_LIMIT_PER_MINUTE: int = 60

    # --- AI Agent ---
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    AGENT_MAX_TOKENS: int = 2048
    AGENT_TEMPERATURE: float = 0.7

    # --- Agent-specific ---
    USAGE_TRACKING_INTERVAL_HOURS: int = 24
    MATCH_EXPIRY_MINUTES: int = 30
    CIRCUIT_BREAKER_THRESHOLD: float = 0.85
    MAX_CONCURRENT_MATCHES: int = 5


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


settings = get_settings()
