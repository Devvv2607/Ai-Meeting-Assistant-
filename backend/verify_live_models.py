"""
Verification script for LiveSession and Speaker models.
This script verifies that both models match the design schema.
"""
import sys
sys.path.insert(0, '.')

from app.models.live_session import LiveSession
from app.models.speaker import Speaker
from app.models.meeting import Meeting

def verify_model_fields(model_class, expected_fields):
    """Verify that a model has all expected fields."""
    actual_fields = {c.name for c in model_class.__table__.columns}
    missing_fields = set(expected_fields) - actual_fields
    extra_fields = actual_fields - set(expected_fields)
    
    return {
        'actual': actual_fields,
        'missing': missing_fields,
        'extra': extra_fields,
        'matches': len(missing_fields) == 0
    }

def main():
    print("=" * 60)
    print("LiveSession and Speaker Model Verification")
    print("=" * 60)
    
    # Expected fields from design.md
    expected_live_session_fields = {
        'id', 'meeting_id', 'session_token', 'status', 
        'started_at', 'ended_at', 'duration_seconds', 'error_message'
    }
    
    expected_speaker_fields = {
        'id', 'meeting_id', 'speaker_number', 'speaker_name',
        'talk_time_seconds', 'word_count', 'created_at'
    }
    
    # Verify LiveSession model
    print("\n1. LiveSession Model Verification")
    print("-" * 60)
    live_session_result = verify_model_fields(LiveSession, expected_live_session_fields)
    print(f"Expected fields: {sorted(expected_live_session_fields)}")
    print(f"Actual fields:   {sorted(live_session_result['actual'])}")
    
    if live_session_result['matches']:
        print("✓ LiveSession model has all required fields")
    else:
        if live_session_result['missing']:
            print(f"✗ Missing fields: {live_session_result['missing']}")
        if live_session_result['extra']:
            print(f"  Extra fields: {live_session_result['extra']}")
    
    # Verify Speaker model
    print("\n2. Speaker Model Verification")
    print("-" * 60)
    speaker_result = verify_model_fields(Speaker, expected_speaker_fields)
    print(f"Expected fields: {sorted(expected_speaker_fields)}")
    print(f"Actual fields:   {sorted(speaker_result['actual'])}")
    
    if speaker_result['matches']:
        print("✓ Speaker model has all required fields")
    else:
        if speaker_result['missing']:
            print(f"✗ Missing fields: {speaker_result['missing']}")
        if speaker_result['extra']:
            print(f"  Extra fields: {speaker_result['extra']}")
    
    # Verify relationships
    print("\n3. Relationship Verification")
    print("-" * 60)
    
    # Check LiveSession relationships
    live_session_rels = {rel.key for rel in LiveSession.__mapper__.relationships}
    print(f"LiveSession relationships: {live_session_rels}")
    if 'meeting' in live_session_rels:
        print("✓ LiveSession has 'meeting' relationship")
    else:
        print("✗ LiveSession missing 'meeting' relationship")
    
    # Check Speaker relationships
    speaker_rels = {rel.key for rel in Speaker.__mapper__.relationships}
    print(f"Speaker relationships: {speaker_rels}")
    if 'meeting' in speaker_rels:
        print("✓ Speaker has 'meeting' relationship")
    else:
        print("✗ Speaker missing 'meeting' relationship")
    
    # Check Meeting relationships
    meeting_rels = {rel.key for rel in Meeting.__mapper__.relationships}
    print(f"Meeting relationships: {meeting_rels}")
    if 'live_session' in meeting_rels:
        print("✓ Meeting has 'live_session' relationship")
    else:
        print("✗ Meeting missing 'live_session' relationship")
    
    if 'speakers' in meeting_rels:
        print("✓ Meeting has 'speakers' relationship")
    else:
        print("✗ Meeting missing 'speakers' relationship")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    all_checks_passed = (
        live_session_result['matches'] and
        speaker_result['matches'] and
        'meeting' in live_session_rels and
        'meeting' in speaker_rels and
        'live_session' in meeting_rels and
        'speakers' in meeting_rels
    )
    
    if all_checks_passed:
        print("✓ All verification checks passed!")
        print("✓ LiveSession model matches design schema")
        print("✓ Speaker model matches design schema")
        print("✓ All relationships are properly configured")
        return 0
    else:
        print("✗ Some verification checks failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
