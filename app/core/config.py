import json
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings for Reliable Assurance FastAPI Backend.
    Enforces strict environment separation and safety checks.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Application Information
    APP_NAME: str = "Reliable Assurance Backend"
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000

    # Local Development Database Configuration
    DATABASE_URL: str = "mysql+aiomysql://root:password@localhost:3306/reliable_insurance_dev"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_RECYCLE: int = 3600
    DB_ECHO: bool = False

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CONNECT_TIMEOUT: int = 2

    # Security & JWT Configuration
    JWT_SECRET_KEY: str = "reliable-insurance-default-secret-key-32-chars-minimum"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS Configuration
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://localhost:8000"]

    # Phase 11 Document & File Storage Configuration (Local-First)
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_ROOT: str = "./storage_data"
    MAX_UPLOAD_SIZE_BYTES: int = 20 * 1024 * 1024
    POLICY_PARSER_WEBHOOK_SECRET: str = "local-dev-policy-parser-webhook-secret"

    # Phase 13 External Integrations & Providers Configuration (Local-First Mock Defaults)
    RC_PROVIDER_TYPE: str = "mock"
    RC_API_KEY: str = "mock-rc-api-key"
    RC_BASE_URL: str = "https://mock.apiclub.in/api/v1/rc_info"
    SIGNZY_BASE_URL: str = "https://mock.signzy.app/api/v3/vehicle/detailedsearches"
    SIGNZY_API_KEY: str = "mock-signzy-api-key"

    SMS_PROVIDER_TYPE: str = "mock"
    FAST2SMS_API_KEY: str = "mock-fast2sms-api-key"
    FAST2SMS_BASE_URL: str = "https://www.fast2sms.com/dev/bulkV2"
    INDIATEXT_USER: str = "mock_relass"
    INDIATEXT_PASSWORD: str = "mock_password"
    INDIATEXT_BASE_URL: str = "http://sms.indiatext.in/api/mt/SendSMS"

    PUSH_PROVIDER_TYPE: str = "mock"
    ONESIGNAL_APP_ID: str = "mock-onesignal-app-id"
    ONESIGNAL_REST_API_KEY: str = "mock-onesignal-rest-api-key"
    ONESIGNAL_BASE_URL: str = "https://onesignal.com/api/v1/notifications"

    EMAIL_PROVIDER_TYPE: str = "mock"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = "mock.reliable.mis1@gmail.com"
    SMTP_PASSWORD: str = "mock-smtp-app-password"
    SMTP_FROM_EMAIL: str = "reliable.mis1@gmail.com"

    OTP_TTL_SECONDS: int = 300
    OTP_MAX_ATTEMPTS: int = 3
    OTP_RESEND_COOLDOWN_SECONDS: int = 60

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url_safety(cls, v: str) -> str:
        """
        Enforce strict database separation rule:
        The legacy production database (brahmainsurance) and remote production IPs
        must NEVER be configured as the runtime database for this application.
        """
        forbidden_patterns = [
            "brahmainsurance",
            "103.149.199.250",
            "103.7.181.105",
            "103.104.73.198"
        ]
        lower_v = v.lower()
        for pattern in forbidden_patterns:
            if pattern.lower() in lower_v:
                raise ValueError(
                    f"CRITICAL SAFETY VIOLATION: '{pattern}' detected in DATABASE_URL. "
                    "The legacy production database must NEVER be used as the runtime database of "
                    "Reliable-Insurance-Backend. Local development must use an independent database (e.g., reliable_insurance_dev)."
                )
        return v

    @field_validator("LOCAL_STORAGE_ROOT", "STORAGE_BACKEND")
    @classmethod
    def validate_storage_safety(cls, v: str) -> str:
        """
        Enforce strict file storage isolation rule:
        Production hosts, production domains, and remote shares must NEVER be used.
        """
        forbidden_patterns = [
            "brahmainsurance",
            "103.149.199.250",
            "103.7.181.105",
            "103.104.73.198",
            "amazonaws.com",
        ]
        lower_v = v.lower()
        for pattern in forbidden_patterns:
            if pattern.lower() in lower_v:
                raise ValueError(
                    f"CRITICAL SAFETY VIOLATION: '{pattern}' detected in storage configuration. "
                    "Phase 11 file storage must remain strictly local."
                )
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("["):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v


settings = Settings()
