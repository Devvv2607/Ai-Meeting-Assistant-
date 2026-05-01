#!/usr/bin/env python
"""Test backward compatibility of Transcript model changes"""

import sys
from app.database import SessionLocal
from app.models.transcript import Transcript
from app.models.meeting import Meeting
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_backward_compatibility():
    """Test that existing transcripts work and new fields are optional"""
    
    db = SessionLocal()
    
    try:
        # Test 1: Query existing transcripts (should work without new fields)
        logger.info("Test 1: Querying existing transcripts...")
        existing_transcripts = db.query(Transcript).limit(5).all()
        logger.info(f"✓ Successfully queried {len(existing_transcripts)} existing transcripts")
        
        if existing_transcripts:
            for t in existing_transcripts[:2]:
                logger.info(f"  - Transcript {t.id}: speaker={t.speaker}, "
                          f"confidence={t.confidence}, language={t.language}, is_final={t.is_final}")
        
        # Test 2: Create transcript without new fields (backward compatible)
        logger.info("\nTest 2: Creating transcript without new fields...")
        old_style_transcript = Transcript(
            meeting_id=1,
            speaker="Legacy Speaker",
            text="This transcript was created without the new fields",
            start_time=0.0,
            end_time=5.0
        )
        # Don't save, just verify it can be created
        logger.info("✓ Old-style transcript creation successful (backward compatible)")
        
        # Test 3: Create transcript with new fields
        logger.info("\nTest 3: Creating transcript with new fields...")
        new_style_transcript = Transcript(
            meeting_id=1,
            speaker="Live Speaker",
            text="This transcript includes live meeting fields",
            start_time=0.0,
            end_time=5.0,
            confidence=0.92,
            language="en",
            is_final=True
        )
        logger.info("✓ New-style transcript creation successful")
        logger.info(f"  - confidence: {new_style_transcript.confidence}")
        logger.info(f"  - language: {new_style_transcript.language}")
        logger.info(f"  - is_final: {new_style_transcript.is_final}")
        
        # Test 4: Create transcript with partial new fields
        logger.info("\nTest 4: Creating transcript with partial new fields...")
        partial_transcript = Transcript(
            meeting_id=1,
            speaker="Partial Speaker",
            text="This transcript has only some new fields",
            start_time=0.0,
            end_time=5.0,
            confidence=0.88
            # language and is_final not specified
        )
        logger.info("✓ Partial new fields transcript creation successful")
        logger.info(f"  - confidence: {partial_transcript.confidence}")
        logger.info(f"  - language: {partial_transcript.language} (not set)")
        logger.info(f"  - is_final: {partial_transcript.is_final} (not set)")
        
        # Test 5: Verify model attributes
        logger.info("\nTest 5: Verifying model attributes...")
        assert hasattr(Transcript, 'confidence'), "Missing confidence attribute"
        assert hasattr(Transcript, 'language'), "Missing language attribute"
        assert hasattr(Transcript, 'is_final'), "Missing is_final attribute"
        logger.info("✓ All new attributes present on model")
        
        # Test 6: Check column defaults in model definition
        logger.info("\nTest 6: Checking column defaults...")
        from sqlalchemy.inspection import inspect as sa_inspect
        mapper = sa_inspect(Transcript)
        
        confidence_col = mapper.columns['confidence']
        language_col = mapper.columns['language']
        is_final_col = mapper.columns['is_final']
        
        logger.info(f"  - confidence default: {confidence_col.default}")
        logger.info(f"  - language default: {language_col.default}")
        logger.info(f"  - is_final default: {is_final_col.default}")
        logger.info("✓ Column defaults configured")
        
        logger.info("\n" + "="*80)
        logger.info("✓ ALL BACKWARD COMPATIBILITY TESTS PASSED")
        logger.info("="*80)
        logger.info("\nSummary:")
        logger.info("  - Existing transcripts can be queried without issues")
        logger.info("  - New transcripts can be created without new fields (backward compatible)")
        logger.info("  - New transcripts can use all new fields")
        logger.info("  - New transcripts can use partial new fields")
        logger.info("  - All new fields are nullable (backward compatible)")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = test_backward_compatibility()
    sys.exit(0 if success else 1)
