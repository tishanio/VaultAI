"""Tests for application configuration."""
from vault.config import settings


def test_app_name():
    assert settings.APP_NAME == "Vault"


def test_app_version():
    assert settings.APP_VERSION == "0.1.0"


def test_demo_mode_default():
    assert settings.DEMO_MODE is True


def test_jwt_algorithm():
    assert settings.JWT_ALGORITHM == "RS256"


def test_platform_fee_percentage():
    assert settings.PLATFORM_FEE_PERCENTAGE == 12.0


def test_rate_limit():
    assert settings.RATE_LIMIT_PER_MINUTE == 60


def test_database_url():
    assert "postgresql+asyncpg" in settings.DATABASE_URL


def test_redis_url():
    assert settings.REDIS_URL.startswith("redis://")
