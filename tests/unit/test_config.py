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


def test_production_jwt_secret_validation_rejects_defaults():
    """
    CRITICAL SECURITY TEST:
    Verify that APP_ENV=production strictly rejects default/placeholder JWT secrets,
    short secrets, or empty values, without leaking secret strings.
    """
    # 1. Reject default placeholder in production
    with pytest.raises(ValidationError) as exc_info:
        Settings(APP_ENV="production")
    assert "JWT_SECRET_KEY must be explicitly provided in production environment" in str(exc_info.value) or \
           "Known development placeholder or default JWT_SECRET_KEY is forbidden in production" in str(exc_info.value)

    # 2. Reject known insecure / short secret in production
    with pytest.raises(ValidationError) as exc_info:
        Settings(APP_ENV="production", JWT_SECRET_KEY="short-secret")
    assert "JWT_SECRET_KEY must be at least 32 characters in production" in str(exc_info.value)

    # 3. Reject empty secret in production
    with pytest.raises(ValidationError) as exc_info:
        Settings(APP_ENV="production", JWT_SECRET_KEY="   ")
    assert "JWT_SECRET_KEY must be explicitly provided in production environment" in str(exc_info.value)

    # 4. Accept strong explicit production secret (32+ chars)
    valid_prod_secret = "a" * 32
    s_prod = Settings(APP_ENV="production", JWT_SECRET_KEY=valid_prod_secret)
    assert s_prod.APP_ENV == "production"
    assert s_prod.JWT_SECRET_KEY == valid_prod_secret


def test_safety_check_prevents_legacy_staging_and_soap_ips():
    """Verify that additional legacy staging quote and SOAP IPs are also blocked."""
    forbidden_urls = [
        "mysql+aiomysql://root:password@103.76.254.139:3306/somedb",
        "mysql+aiomysql://root:password@103.76.188.138:85/somedb",
    ]
    for url in forbidden_urls:
        with pytest.raises(ValidationError) as exc_info:
            Settings(DATABASE_URL=url)
        assert "CRITICAL SAFETY VIOLATION" in str(exc_info.value)


def test_support_contact_configuration():
    """Verify support contact phone number is configurable via Settings."""
    s = Settings()
    assert s.SUPPORT_PHONE_NUMBER == "9822166111"
    s_custom = Settings(SUPPORT_PHONE_NUMBER="1800123456")
    assert s_custom.SUPPORT_PHONE_NUMBER == "1800123456"
