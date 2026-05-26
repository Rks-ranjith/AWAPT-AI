import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "AWAP-AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Security — set SECRET_KEY in production (no insecure default at runtime if unset)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8

    # Comma-separated API keys for CI/CD webhooks (e.g. WEBHOOK_API_KEYS=key1,key2)
    WEBHOOK_API_KEYS: str = os.getenv("WEBHOOK_API_KEYS", "")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///awap.db")

    # Redis for Celery
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6380/0")

    # Scan limits (architecture §11.2)
    SCAN_MAX_PAGES: int = int(os.getenv("SCAN_MAX_PAGES", "50"))
    SCAN_RATE_LIMIT: float = float(os.getenv("SCAN_RATE_LIMIT", "10"))
    MAX_CONCURRENT_CONNECTIONS: int = int(os.getenv("MAX_CONCURRENT_CONNECTIONS", "20"))
    SCAN_PROFILE_DEFAULT: str = os.getenv("SCAN_PROFILE_DEFAULT", "standard")

    # OAST
    OAST_SERVER: str = os.getenv("OAST_SERVER", "")

    # LLM config (optional — rule-based analysis runs without a key)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "anthropic")
    LLM_API_KEY: str | None = os.getenv("LLM_API_KEY")
    LLM_MODEL: str | None = os.getenv("LLM_MODEL")
    LLM_BASE_URL: str | None = os.getenv("LLM_BASE_URL")

    # Optional OSINT keys
    SHODAN_API_KEY: str | None = os.getenv("SHODAN_API_KEY")
    VIRUSTOTAL_API_KEY: str | None = os.getenv("VIRUSTOTAL_API_KEY")

    # SMTP Settings
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "no-reply@awap.ai")

    @property
    def webhook_key_list(self) -> list[str]:
        if not self.WEBHOOK_API_KEYS:
            return []
        return [k.strip() for k in self.WEBHOOK_API_KEYS.split(",") if k.strip()]

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
