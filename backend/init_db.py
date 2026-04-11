#!/usr/bin/env python
"""Initialize database and create tables"""

from app.database import Base, engine
from app.models.user import User
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.summary import Summary
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """Create all tables"""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database tables created successfully!")
        return True
    except Exception as e:
        logger.error(f"✗ Error creating tables: {str(e)}")
        return False

if __name__ == "__main__":
    success = init_db()
    exit(0 if success else 1)
