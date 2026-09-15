import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "organiclink.db").replace("\\", "/")

class Settings(BaseSettings):
    PROJECT_NAME: str = "OrganicLink"
    ENVIRONMENT: str = "production"
    DATABASE_URL: str = f"sqlite:///{DEFAULT_DB_PATH}"
    SECRET_KEY: str = "organiclink-secret-key-change-in-production-2026-irish-organic"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # Administrator setup credentials (optional, for create_admin CLI)
    ADMIN_EMAIL: Optional[str] = None
    ADMIN_PASSWORD: Optional[str] = None
    ADMIN_NAME: Optional[str] = "OrganicLink Administrator"
    ADMIN_PHONE: Optional[str] = None
    
    # CORS Origin Whitelist (comma-separated strings)
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://localhost:5174,http://localhost:80,http://localhost"
    
    # Platform business settings
    VARIANCE_TOLERANCE_PERCENT: float = 10.0
    MIN_LISTING_GRADE: str = "C"
    COMMISSION_PERCENT: float = 5.0
    PAYMENT_TERMS_DAYS: int = 14

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
