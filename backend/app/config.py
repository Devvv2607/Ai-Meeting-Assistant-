import os
from pydantic_settings import BaseSettings
from typing import Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Explicitly load .env file from root directory
env_file_path = Path(__file__).parent.parent.parent / ".env"
if env_file_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file_path)
    logger.info(f"Loaded .env file from: {env_file_path}")
else:
    logger.warning(f".env file not found at: {env_file_path}")


class Settings(BaseSettings):
    """Application settings and configuration"""

    # API Settings
    APP_NAME: str = "AI Meeting Intelligence Platform"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = os.getenv("DEBUG", "False") == "True"

    # Database
    DB_USER: str = os.getenv("DB_USER", "DevM")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "pass@123")
    DB_NAME: str = os.getenv("DB_NAME", "ai_meeting")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5433")
    
    @property
    def DATABASE_URL(self) -> str:
        from urllib.parse import quote
        # URL-encode the password to handle special characters like '@'
        encoded_password = quote(self.DB_PASSWORD, safe='')
        return f"postgresql://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    SQLALCHEMY_POOL_SIZE: int = 20
    SQLALCHEMY_MAX_OVERFLOW: int = 40

    # JWT
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", "your-super-secret-key-change-in-production"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv(
        "CELERY_RESULT_BACKEND", "redis://localhost:6379/2"
    )

    # AWS S3
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "ai-meeting-bucket")
    S3_ENDPOINT_URL: Optional[str] = os.getenv("S3_ENDPOINT_URL", None)

    # Whisper Settings
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
    CHUNK_DURATION: int = 300  # 5 minutes in seconds
    DEVICE: str = os.getenv("DEVICE", "cpu")  # cuda or cpu

    # LLM Settings
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GROQ_API_KEY", "")  # Backward compatibility
    LLM_API_KEY: str = os.getenv("GROQ_API_KEY", "")  # Alias for compatibility
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")  # groq, gemini, mistral or llama

    # Embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # File Upload
    MAX_FILE_SIZE: int = 2 * 1024 * 1024 * 1024  # 2GB
    ALLOWED_AUDIO_FORMATS: list = [".wav", ".mp3", ".m4a", ".mp4"]

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 3600  # seconds

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


settings = Settings()


def validate_required_settings():
    """Validate that required environment variables are set"""
    required_vars = {
        "DB_USER": settings.DB_USER,
        "DB_PASSWORD": settings.DB_PASSWORD,
        "DB_NAME": settings.DB_NAME,
        "DB_HOST": settings.DB_HOST,
        "DB_PORT": settings.DB_PORT,
    }
    
    missing_vars = []
    for var_name, var_value in required_vars.items():
        if not var_value or var_value == "":
            missing_vars.append(var_name)
    
    if missing_vars:
        error_msg = f"Missing or invalid required environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        logger.error("Please set these variables in your .env file or environment")
        raise ValueError(error_msg)
    
    # Validate database connection string
    try:
        db_url = settings.DATABASE_URL
        logger.info(f"Database URL configured: postgresql://{settings.DB_USER}:***@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    except Exception as e:
        logger.error(f"Error constructing database URL: {e}")
        raise
    
    # Warn if using default SECRET_KEY
    if settings.SECRET_KEY == "your-super-secret-key-change-in-production":
        logger.warning("Using default SECRET_KEY - this is insecure for production!")
    
    logger.info("All required environment variables are set")
    return True
