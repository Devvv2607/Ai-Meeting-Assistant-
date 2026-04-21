from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Database connection
# Use StaticPool for SQLite, QueuePool for PostgreSQL
try:
    if "sqlite" in settings.DATABASE_URL:
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=settings.DEBUG,
        )
        logger.info("Using SQLite database with StaticPool")
    else:
        from sqlalchemy.pool import QueuePool
        engine = create_engine(
            settings.DATABASE_URL,
            poolclass=QueuePool,
            pool_size=settings.SQLALCHEMY_POOL_SIZE,
            max_overflow=settings.SQLALCHEMY_MAX_OVERFLOW,
            echo=settings.DEBUG,
            pool_pre_ping=True,  # Enable connection health checks
        )
        logger.info(f"Using PostgreSQL database with QueuePool (pool_size={settings.SQLALCHEMY_POOL_SIZE}, max_overflow={settings.SQLALCHEMY_MAX_OVERFLOW})")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    logger.error(f"Database URL: postgresql://{settings.DB_USER}:***@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_database_connection():
    """Test database connection and return status"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        logger.error(f"Connection string: postgresql://{settings.DB_USER}:***@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
        return False
