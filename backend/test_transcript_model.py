#!/usr/bin/env python
"""Test script to verify Transcript model with new live meeting fields"""

import sys
from app.database import SessionLocal, test_database_connection
from app.models.transcript import Transcript
from app.models.meeting import Meeting
from app.models.user import User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_transcript_model():
    """Test that Transcript model can be imported and used with new fields"""
    
    # Test database connection
    logger.info("Testing database connection...")
    if not test_database_connection():
        logger.error("Database connection failed")
        return False
    
    logger.info("✓ Database connection successful")
    
    # Test model import
    logger.info("Testing Transcript model import...")
    try:
        # Verify the model has the new fields
        assert hasattr(Transcript, 'confidence'), "Missing 'confidence' field"
        assert hasattr(Transcript, 'language'), "Missing 'language' field"
        assert hasattr(Transcript, 'is_final'), "Missing 'is_final' field"
        logger.info("✓ Transcript model has all required fields")
    except AssertionError as e:
        logger.error(f"✗ Model validation failed: {e}")
        return False
    
    # Test creating a transcript instance (without saving to DB)
    logger.info("Testing Transcript instance creation...")
    try:
        transcript = Transcript(
            meeting_id=1,
            speaker="Test Speaker",
            text="This is a test transcript",
            start_time=0.0,
            end_time=5.0,
            confidence=0.95,
            language="en",
            is_final=True
        )
        
        # Verify field values
        assert transcript.confidence == 0.95, "Confidence field not set correctly"
        assert transcript.language == "en", "Language field not set correctly"
        assert transcript.is_final == True, "is_final field not set correctly"
        
        logger.info("✓ Transcript instance created successfully")
        logger.info(f"  - confidence: {transcript.confidence}")
        logger.info(f"  - language: {transcript.language}")
        logger.info(f"  - is_final: {transcript.is_final}")
    except Exception as e:
        logger.error(f"✗ Instance creation failed: {e}")
        return False
    
    # Test default values
    logger.info("Testing default values...")
    try:
        transcript_defaults = Transcript(
            meeting_id=1,
            speaker="Test Speaker",
            text="Test with defaults",
            start_time=0.0,
            end_time=5.0
        )
        
        # Verify defaults (these will be set when saved to DB)
        logger.info("✓ Transcript with defaults created successfully")
        logger.info(f"  - confidence default: {transcript_defaults.confidence}")
        logger.info(f"  - language default: {transcript_defaults.language}")
        logger.info(f"  - is_final default: {transcript_defaults.is_final}")
    except Exception as e:
        logger.error(f"✗ Default values test failed: {e}")
        return False
    
    # Test querying existing transcripts (if any)
    logger.info("Testing database query...")
    db = SessionLocal()
    try:
        # Query first transcript to verify schema is updated
        transcript_count = db.query(Transcript).count()
        logger.info(f"✓ Found {transcript_count} existing transcripts in database")
        
        if transcript_count > 0:
            first_transcript = db.query(Transcript).first()
            logger.info(f"  - First transcript ID: {first_transcript.id}")
            logger.info(f"  - Has confidence field: {hasattr(first_transcript, 'confidence')}")
            logger.info(f"  - Has language field: {hasattr(first_transcript, 'language')}")
            logger.info(f"  - Has is_final field: {hasattr(first_transcript, 'is_final')}")
    except Exception as e:
        logger.error(f"✗ Database query failed: {e}")
        return False
    finally:
        db.close()
    
    logger.info("\n" + "="*60)
    logger.info("✓ ALL TESTS PASSED")
    logger.info("="*60)
    logger.info("\nTranscript model successfully extended with:")
    logger.info("  - confidence (Float): Transcription confidence score (0.0-1.0)")
    logger.info("  - language (String): Detected language code (max 10 chars)")
    logger.info("  - is_final (Boolean): Whether transcript is final or interim")
    logger.info("\nMigration applied successfully!")
    
    return True


if __name__ == "__main__":
    success = test_transcript_model()
    sys.exit(0 if success else 1)
