"""Verify Summary table schema"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine
from sqlalchemy import inspect


def verify_schema():
    """Verify that all new columns exist in the summaries table"""
    inspector = inspect(engine)
    columns = inspector.get_columns('summaries')
    
    print("Summaries table columns:")
    print("-" * 50)
    
    required_new_columns = ['decisions', 'risks', 'next_steps', 'topics', 'meeting_analytics']
    found_columns = []
    
    for col in columns:
        col_name = col['name']
        col_type = str(col['type'])
        print(f"  {col_name:25} {col_type}")
        
        if col_name in required_new_columns:
            found_columns.append(col_name)
    
    print("-" * 50)
    print("\nVerification:")
    
    for col in required_new_columns:
        if col in found_columns:
            print(f"  ✓ {col} - Found")
        else:
            print(f"  ✗ {col} - Missing")
    
    if len(found_columns) == len(required_new_columns):
        print("\n✅ All required columns are present!")
    else:
        print(f"\n❌ Missing {len(required_new_columns) - len(found_columns)} columns")


if __name__ == "__main__":
    verify_schema()
