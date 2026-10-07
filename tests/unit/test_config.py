import pytest
from pydantic import ValidationError
from app.core.config import Settings


def test_settings_default_values():
    """Verify default configuration loads with expected development settings."""
    settings = Settings()
    assert settings.APP_NAME == "Reliable Assurance Backend"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert "reliable_insurance_dev" in settings.DATABASE_URL
    assert "brahmainsurance" not in settings.DATABASE_URL


def test_safety_check_prevents_production_database():
    """
    CRITICAL SAFETY TEST:
    Verify that attempting to configure the legacy production database (brahmainsurance)
    or production IP addresses immediately triggers a validation error.
    """
    forbidden_urls = [
        "mysql+aiomysql://admin_sa:secret@103.149.199.250:3309/brahmainsurance",
        "mysql+aiomysql://root:password@localhost:3306/brahmainsurance",
        "mysql+aiomysql://admin_sa:secret@103.7.181.105:3309/somedb",
        "mysql+aiomysql://admin_sa:secret@103.104.73.198:3306/somedb",
    ]

    for forbidden_url in forbidden_urls:
        with pytest.raises(ValidationError) as exc_info:
            Settings(DATABASE_URL=forbidden_url)
        assert "CRITICAL SAFETY VIOLATION" in str(exc_info.value)


def test_cors_origins_parsing():
    """Verify CORS origins parse lists, JSON strings, and comma-separated values."""
    s1 = Settings(CORS_ORIGINS=["http://localhost:3000"])
    assert s1.CORS_ORIGINS == ["http://localhost:3000"]

    s2 = Settings(CORS_ORIGINS="http://localhost:3000,http://example.com")
    assert s2.CORS_ORIGINS == ["http://localhost:3000", "http://example.com"]
