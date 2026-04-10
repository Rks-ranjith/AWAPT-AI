import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AWAP-AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-prod")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///awap.db")
    
    # Redis for Celery
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6380/0")
    
    # LLM config
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "anthropic")
    LLM_API_KEY: str | None = os.getenv("LLM_API_KEY")

    class Config:
        case_sensitive = True

settings = Settings()
