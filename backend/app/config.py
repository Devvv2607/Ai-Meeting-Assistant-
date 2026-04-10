import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings and configuration"""

    # API Settings
    APP_NAME: str = "AI Meeting Intelligence Platform"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = os.getenv("DEBUG", "False") == "True"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://user:password@localhost:5432/ai_meeting"
    )
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
    DEVICE: str = os.getenv("DEVICE", "cuda")  # cuda or cpu

    # LLM Settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    LLM_API_KEY: str = os.getenv("GEMINI_API_KEY", "")  # Alias for compatibility
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-1.5-flash")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")  # gemini, mistral or llama

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


settings = Settings()
