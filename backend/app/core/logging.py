# backend/app/core/logging.py
"""
Logging Configuration
Centralized logging setup for the application.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from app.core.config import settings

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
JSON_LOG_FORMAT = '{"time": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s", "module": "%(module)s", "funcName": "%(funcName)s", "lineno": %(lineno)d}'

def setup_logging():
    """Setup application logging."""
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if settings.LOG_FORMAT == "json":
        console_formatter = logging.Formatter(JSON_LOG_FORMAT)
    else:
        console_formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    logger.addHandler(console_handler)
    
    # File handler
    file_handler = RotatingFileHandler(
        filename=settings.LOG_FILE,
        maxBytes=settings.LOG_MAX_SIZE,
        backupCount=settings.LOG_BACKUP_COUNT
    )
    file_formatter = logging.Formatter(JSON_LOG_FORMAT)
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    
    # SQLAlchemy logging
    logging.getLogger('sqlalchemy.engine').setLevel(
        logging.INFO if settings.SQL_ECHO else logging.WARNING
    )
    
    # Uvicorn logging
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    
    return logger

# Create logger instance
logger = setup_logging()

# Convenience functions
def get_logger(name: str) -> logging.Logger:
    """Get a named logger."""
    return logging.getLogger(name)

def log_exception(exc: Exception, context: str = ""):
    """Log an exception with context."""
    logger.error(f"{context}: {str(exc)}", exc_info=True)

def log_api_request(method: str, path: str, status_code: int, duration: float):
    """Log API request details."""
    logger.info(f"API {method} {path} - {status_code} ({duration:.3f}s)")

def log_background_job(job_type: str, job_id: str, status: str, details: str = ""):
    """Log background job activity."""
    logger.info(f"Job {job_type} - {job_id} - {status} {details}")