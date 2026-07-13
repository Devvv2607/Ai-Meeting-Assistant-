import os
from pydantic_settings import BaseSettings
from typing import Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Load .env from the repo root when present (local development only).
# load_dotenv never overrides variables already set in the process
# environment, so platform-injected vars (Railway, Docker) always win.
# In production no .env exists and none is required.
env_file_path = Path(__file__).parent.parent.parent / ".env"
if env_file_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file_path)
    logger.info(f"Loaded .env file from: {env_file_path}")
else:
    logger.info(".env file not found — using process environment (expected in production)")

# Configure ffmpeg (bundled via imageio-ffmpeg) before any pydub conversion runs.
try:
    from app.ffmpeg_setup import configure_ffmpeg
    configure_ffmpeg()
except Exception as _ffmpeg_err:  # never block startup on ffmpeg setup
    logger.warning(f"ffmpeg setup skipped: {_ffmpeg_err}")


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
        # A full DATABASE_URL in the environment (the Railway/Heroku
        # convention) always wins over the DB_* parts and their local
        # defaults. SQLAlchemy 2.x rejects the legacy postgres:// scheme,
        # so normalize it.
        env_url = os.getenv("DATABASE_URL")
        if env_url:
            if env_url.startswith("postgres://"):
                env_url = "postgresql://" + env_url[len("postgres://"):]
            return env_url

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

    # Supabase Auth (GoTrue) — when both are set, user credentials are
    # stored/verified by Supabase instead of the local users table.
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")

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

    # Live-meeting audio capture (env-configurable).
    # NOTE: single-instance / dev only. Files written here are EPHEMERAL on
    # Cloud Run (lost on instance restart) — same constraint as the #1
    # module-state blocker. GCS is the deploy-time replacement; not built here.
    LIVE_AUDIO_DIR: str = os.getenv("LIVE_AUDIO_DIR", "backend/uploads/live_audio")

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
        # Fail closed: the app's core features (transcription, summary, chat) are
        # useless without a Groq key, so refuse to boot rather than silently
        # serving fallback text on every request.
        "GROQ_API_KEY": settings.GROQ_API_KEY,
    }
    # DB config comes either from a single DATABASE_URL (Railway/Heroku
    # convention) or from the DB_* parts — only require the parts when no
    # full URL is provided.
    if not os.getenv("DATABASE_URL"):
        required_vars.update({
            "DB_USER": settings.DB_USER,
            "DB_PASSWORD": settings.DB_PASSWORD,
            "DB_NAME": settings.DB_NAME,
            "DB_HOST": settings.DB_HOST,
            "DB_PORT": settings.DB_PORT,
        })
    
    missing_vars = []
    for var_name, var_value in required_vars.items():
        if not var_value or var_value == "":
            missing_vars.append(var_name)
    
    if missing_vars:
        error_msg = f"Missing or invalid required environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        logger.error("Please set these variables in your .env file or environment")
        raise ValueError(error_msg)
    
    # Validate database connection string (log with the password masked)
    try:
        from urllib.parse import urlsplit
        parts = urlsplit(settings.DATABASE_URL)
        host = parts.hostname or "?"
        port = f":{parts.port}" if parts.port else ""
        logger.info(
            f"Database URL configured: {parts.scheme}://{parts.username}:***@{host}{port}{parts.path}"
        )
        source = "DATABASE_URL env var" if os.getenv("DATABASE_URL") else "DB_* variables/defaults"
        logger.info(f"Database config source: {source}")

        auth_provider = (
            f"Supabase Auth ({settings.SUPABASE_URL})"
            if settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY
            else "local password hashes (SUPABASE_URL/SUPABASE_ANON_KEY not set)"
        )
        logger.info(f"Auth credential provider: {auth_provider}")
    except Exception as e:
        logger.error(f"Error constructing database URL: {e}")
        raise
    
    # Warn if using default SECRET_KEY
    if settings.SECRET_KEY == "your-super-secret-key-change-in-production":
        logger.warning("Using default SECRET_KEY - this is insecure for production!")
    
    logger.info("All required environment variables are set")
    return True
