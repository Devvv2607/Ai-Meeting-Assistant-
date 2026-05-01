"""
Integration test for LiveSessionManager

This test verifies the complete lifecycle of a live session:
1. Create session
2. Track activity
3. End session
4. Verify database records
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.user import User
from app.models.meeting import Meeting, MeetingStatus
from app.models.live_session import LiveSession
from app.services.live_session_manager import LiveSessionManager


def test_live_session_lifecycle():
    """Test complete lifecycle of a live session"""
    
    # Setup test database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Create test user
        user = User(
            email="integration@test.com",
            password_hash="test_hash",
            full_name="Integration Test User"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Initialize session manager
        manager = LiveSessionManager(db)
        
        # Step 1: Create session
        print("Step 1: Creating live session...")
        live_session = manager.create_session(
            user_id=user.id,
            meeting_title="Integration Test Meeting"
        )
        
        assert live_session is not None
        assert live_session.status == "ACTIVE"
        assert live_session.session_token is not None
        print(f"✓ Created session {live_session.id} with token {live_session.session_token[:16]}...")
        
        # Verify meeting created
        meeting = db.query(Meeting).filter(
            Meeting.id == live_session.meeting_id
        ).first()
        assert meeting is not None
        assert meeting.title == "Integration Test Meeting"
        assert meeting.status == MeetingStatus.PROCESSING.value
        print(f"✓ Meeting {meeting.id} created with status {meeting.status}")
        
        # Step 2: Simulate activity
        print("\nStep 2: Simulating session activity...")
        for i in range(5):
            manager.update_segment_count(live_session.session_token)
        
        state = manager.get_session_state(live_session.session_token)
        assert state.segment_count == 5
        print(f"✓ Processed {state.segment_count} segments")
        
        # Verify session is active
        assert manager.is_session_active(live_session.session_token)
        assert manager.get_active_session_count() == 1
        print(f"✓ Session is active (total active: {manager.get_active_session_count()})")
        
        # Step 3: End session
        print("\nStep 3: Ending session...")
        finalized_meeting = manager.end_session(live_session.session_token)
        
        assert finalized_meeting.status == MeetingStatus.COMPLETED.value
        assert finalized_meeting.duration is not None
        assert finalized_meeting.duration >= 0
        print(f"✓ Meeting finalized with duration {finalized_meeting.duration:.3f}s")
        
        # Verify live session updated
        updated_session = db.query(LiveSession).filter(
            LiveSession.id == live_session.id
        ).first()
        assert updated_session.status == "ENDED"
        assert updated_session.ended_at is not None
        assert updated_session.duration_seconds is not None
        print(f"✓ LiveSession status: {updated_session.status}")
        
        # Verify session removed from memory
        assert not manager.is_session_active(live_session.session_token)
        assert manager.get_active_session_count() == 0
        print(f"✓ Session removed from memory (active count: {manager.get_active_session_count()})")
        
        print("\n✅ Integration test PASSED - All lifecycle steps completed successfully!")
        
    finally:
        db.close()


if __name__ == "__main__":
    test_live_session_lifecycle()
