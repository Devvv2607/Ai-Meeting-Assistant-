#!/usr/bin/env python
"""Initialize database and create tables

NOTE: For schema changes, use Alembic migrations instead of this script.
This script is only for initial database setup.

To create migrations:
    venv_local\Scripts\python.exe -m alembic -c alembic.ini revision --autogenerate -m "Description"

To apply migrations:
    venv_local\Scripts\python.exe -m alembic -c alembic.ini upgrade head
"""

from app.database import Base, engine
from app.models.user import User
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.summary import Summary
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """Create all tables
    
    WARNING: This creates tables directly without migration tracking.
    For production, use Alembic migrations instead.
    """
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database tables created successfully!")
        logger.info("\nFor future schema changes, use Alembic migrations:")
        logger.info("  1. Create migration: alembic revision --autogenerate -m 'description'")
        logger.info("  2. Apply migration: alembic upgrade head")
        return True
    except Exception as e:
        logger.error(f"✗ Error creating tables: {str(e)}")
        return False

if __name__ == "__main__":
    success = init_db()
    exit(0 if success else 1)
