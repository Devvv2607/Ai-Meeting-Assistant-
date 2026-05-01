#!/usr/bin/env python
"""Verify database schema for transcripts table"""

from sqlalchemy import inspect, text
from app.database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verify_schema():
    """Verify the transcripts table schema"""
    
    logger.info("Verifying transcripts table schema...")
    
    inspector = inspect(engine)
    
    # Get columns for transcripts table
    columns = inspector.get_columns('transcripts')
    
    logger.info("\nTranscripts table columns:")
    logger.info("=" * 80)
    
    for col in columns:
        nullable = "NULL" if col['nullable'] else "NOT NULL"
        default = f" DEFAULT {col['default']}" if col['default'] else ""
        logger.info(f"  {col['name']:20} {str(col['type']):20} {nullable:10}{default}")
    
    # Check for required columns
    column_names = [col['name'] for col in columns]
    required_columns = ['confidence', 'language', 'is_final']
    
    logger.info("\n" + "=" * 80)
    logger.info("Verification Results:")
    logger.info("=" * 80)
    
    all_present = True
    for col_name in required_columns:
        if col_name in column_names:
            logger.info(f"✓ Column '{col_name}' exists")
        else:
            logger.error(f"✗ Column '{col_name}' is missing")
            all_present = False
    
    if all_present:
        logger.info("\n✓ All required columns are present!")
        
        # Get column details
        for col in columns:
            if col['name'] in required_columns:
                logger.info(f"\n{col['name']}:")
                logger.info(f"  Type: {col['type']}")
                logger.info(f"  Nullable: {col['nullable']}")
                logger.info(f"  Default: {col['default']}")
    
    return all_present


if __name__ == "__main__":
    import sys
    success = verify_schema()
    sys.exit(0 if success else 1)
