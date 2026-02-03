# backend/app/core/config.py
import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Environment
    DEBUG: bool = False
    LOG_FORMAT: str = "%(levelname)s | %(asctime)s | %(name)s | %(message)s"
    LOG_FILE: str = "logs/app.log"
    LOG_MAX_SIZE: int = 10 * 1024 * 1024   # 10 MB
    LOG_BACKUP_COUNT: int = 5
    LOG_FORMAT: str = "text" 


    # API
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "AI Resume Intake & HR Platform"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/hr_platform"
    DATABASE_POOL_SIZE: int = 20             
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800   
    SQL_ECHO: bool = False
    
    # CORS
    BACKEND_CORS_ORIGINS: list = ["http://localhost:8080", "https://your-production-frontend.com"]
    
    # File upload
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Mock mode
    MOCK_MODE: bool = True
    
    class Config:
        env_file = ".env",
        extra = "ignore"

settings = Settings()