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
