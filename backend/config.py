import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "OrganicLink"
    DATABASE_URL: str = "sqlite:///./organiclink.db"
    SECRET_KEY: str = "organiclink-secret-key-change-in-production-2026-irish-organic"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # Platform business settings
    VARIANCE_TOLERANCE_PERCENT: float = 10.0
    MIN_LISTING_GRADE: str = "C"
    COMMISSION_PERCENT: float = 5.0
    PAYMENT_TERMS_DAYS: int = 14

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
