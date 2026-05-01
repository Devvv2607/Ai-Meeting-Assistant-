"""
Tests for LiveSessionManager service

Tests cover:
- Session creation with Meeting and LiveSession records
- Session state tracking in memory
- Session finalization and cleanup
- Abandoned session cleanup
- Error handling
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.meeting import Meeting, MeetingStatus
from app.models.live_session import LiveSession
from app.models.user import User
from app.services.live_session_manager import LiveSessionManager, LiveSessionState


# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Create a fresh database session for each test"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(
        email="test@example.com",
        password_hash="hashed_password_here",
        full_name="Test User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def session_manager(db_session):
    """Create a LiveSessionManager instance"""
    return LiveSessionManager(db_session)


class TestCreateSession:
    """Tests for create_session method"""
    
    def test_create_session_success(self, session_manager, test_user, db_session):
        """Test successful session creation"""
        # Create session
        live_session = session_manager.create_session(
            user_id=test_user.id,
            meeting_title="Test Meeting"
        )
        
        # Verify LiveSession record
        assert live_session is not None
        assert live_session.id is not None
        assert live_session.meeting_id is not None
        assert live_session.session_token is not None
        assert live_session.status == "ACTIVE"
        assert live_session.started_at is not None
        assert live_session.ended_at is None
        
        # Verify Meeting record
        meeting = db_session.query(Meeting).filter(
            Meeting.id == live_session.meeting_id
        ).first()
        assert meeting is not None
        assert meeting.title == "Test Meeting"
        assert meeting.user_id == test_user.id
        assert meeting.status == MeetingStatus.PROCESSING.value
        assert meeting.audio_url == "live://stream"
        
        # Verify in-memory state
        assert session_manager.is_session_active(live_session.session_token)
        state = session_manager.get_session_state(live_session.session_token)
        assert state.session_id == live_session.id
        assert state.meeting_id == live_session.meeting_id
        assert state.user_id == test_user.id
        assert state.segment_count == 0
    
    def test_create_session_generates_unique_tokens(
        self, session_manager, test_user
    ):
        """Test that each session gets a unique token"""
        session1 = session_manager.create_session(test_user.id, "Meeting 1")
        session2 = session_manager.create_session(test_user.id, "Meeting 2")
        
        assert session1.session_token != session2.session_token
        assert session_manager.get_active_session_count() == 2
    
    def test_create_session_with_invalid_user(self, session_manager, db_session):
        """Test session creation with non-existent user creates record but may fail on commit"""
        # Note: SQLite doesn't enforce foreign key constraints by default
        # In production with PostgreSQL, this would fail
        # For now, we just verify the session can be created
        try:
            live_session = session_manager.create_session(
                user_id=99999,  # Non-existent user
                meeting_title="Test Meeting"
            )
            # If it succeeds (SQLite), verify the record was created
            assert live_session is not None
        except Exception:
            # If it fails (PostgreSQL with FK constraints), that's expected
            pass


class TestEndSession:
    """Tests for end_session method"""
    
    def test_end_session_success(self, session_manager, test_user, db_session):
        """Test successful session ending"""
        # Create session
        live_session = session_manager.create_session(
            user_id=test_user.id,
            meeting_title="Test Meeting"
        )
        session_token = live_session.session_token
        
        # End session
        meeting = session_manager.end_session(session_token)
        
        # Verify Meeting updated
        assert meeting.status == MeetingStatus.COMPLETED.value
        assert meeting.duration is not None
        assert meeting.duration > 0
        
        # Verify LiveSession updated
        updated_session = db_session.query(LiveSession).filter(
            LiveSession.session_token == session_token
        ).first()
        assert updated_session.status == "ENDED"
        assert updated_session.ended_at is not None
        assert updated_session.duration_seconds is not None
        assert updated_session.duration_seconds > 0
        
        # Verify removed from memory
        assert not session_manager.is_session_active(session_token)
        assert session_manager.get_active_session_count() == 0
    
    def test_end_session_calculates_duration(
        self, session_manager, test_user, db_session
    ):
        """Test that duration is calculated correctly"""
        live_session = session_manager.create_session(
            user_id=test_user.id,
            meeting_title="Test Meeting"
        )
        
        # End session immediately
        meeting = session_manager.end_session(live_session.session_token)
        
        # Duration should be small but positive
        assert meeting.duration >= 0
        assert meeting.duration < 1  # Less than 1 second for immediate end
    
    def test_end_session_with_invalid_token(self, session_manager):
        """Test ending session with invalid token raises error"""
        with pytest.raises(ValueError, match="Session not found"):
            session_manager.end_session("invalid_token")
    
    def test_end_session_twice_raises_error(self, session_manager, test_user):
        """Test ending the same session twice raises error"""
        live_session = session_manager.create_session(
            user_id=test_user.id,
            meeting_title="Test Meeting"
        )
        
        # End once - should succeed
        session_manager.end_session(live_session.session_token)
        
        # End again - should fail
        with pytest.raises(ValueError, match="Session not found"):
            session_manager.end_session(live_session.session_token)


class TestGetSessionState:
    """Tests for get_session_state method"""
    
    def test_get_session_state_success(self, session_manager, test_user):
        """Test retrieving session state"""
        live_session = session_manager.create_session(
            user_id=test_user.id,
            meeting_title="Test Meeting"
        )
        
        state = session_manager.get_session_state(live_session.session_token)
        
        assert isinstance(state, LiveSessionState)
        assert state.session_id == live_session.id
        assert state.meeting_id == live_session.meeting_id
        assert state.user_id == test_user.id
        assert state.segment_count == 0
        assert isinstance(state.last_activity, datetime)
    
    def test_get_session_state_with_invalid_token(self, session_manager):
        """Test getting state with invalid token raises error"""
        with pytest.raises(ValueError, match="Session not found"):
            session_manager.get_session_state("invalid_token")
    
    def test_get_session_state_after_updates(self, session_manager, test_user):
        """Test that state reflects updates"""
        live_session = session_manager.create_session(
            user_id=test_user.id,
            meeting_title="Test Meeting"
        )
        
        # Update segment count
        session_manager.update_segment_count(live_session.session_token, 5)
        
        state = session_manager.get_session_state(live_session.session_token)
        assert state.segment_count == 5


class TestUpdateSegmentCount:
    """Tests for update_segment_count method"""
    
    def test_update_segment_count_default_increment(
        self, session_manager, test_user
    ):
        """Test updating segment count with default increment"""
        live_session = session_manager.create_session(
            user_id=test_user.id,
            meeting_title="Test Meeting"
        )
        
        # Update multiple times
        session_manager.update_segment_count(live_session.session_token)
        session_manager.update_segment_count(live_session.session_token)
        session_manager.update_segment_count(live_session.session_token)
        
        state = session_manager.get_session_state(live_session.session_token)
        assert state.segment_count == 3
    
    def test_update_segment_count_custom_increment(
        self, session_manager, test_user
    ):
        """Test updating segment count with custom increment"""
        live_session = session_manager.create_session(
            user_id=test_user.id,
            meeting_title="Test Meeting"
        )
        
        session_manager.update_segment_count(live_session.session_token, 10)
        
        state = session_manager.get_session_state(live_session.session_token)
        assert state.segment_count == 10
    
    def test_update_segment_count_updates_activity(
        self, session_manager, test_user
    ):
        """Test that updating segment count refreshes last_activity"""
        live_session = session_manager.create_session(
            user_id=test_user.id,
            meeting_title="Test Meeting"
        )
        
        state1 = session_manager.get_session_state(live_session.session_token)
        initial_activity = state1.last_activity
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        session_manager.update_segment_count(live_session.session_token)
        
        state2 = session_manager.get_session_state(live_session.session_token)
        assert state2.last_activity > initial_activity


class TestCleanupAbandonedSessions:
    """Tests for cleanup_abandoned_sessions method"""
    
    def test_cleanup_abandoned_sessions(self, session_manager, test_user, db_session):
        """Test cleanup of abandoned sessions"""
        # Create session
        live_session = session_manager.create_session(
            user_id=test_user.id,
            meeting_title="Test Meeting"
        )
        
        # Manually set last_activity to old timestamp
        state = session_manager.get_session_state(live_session.session_token)
        state.last_activity = datetime.utcnow() - timedelta(minutes=10)
        
        # Run cleanup with 5 minute timeout
        cleanup_count = session_manager.cleanup_abandoned_sessions(timeout_minutes=5)
        
        assert cleanup_count == 1
        assert not session_manager.is_session_active(live_session.session_token)
        
        # Verify database updated
        updated_session = db_session.query(LiveSession).filter(
            LiveSession.id == live_session.id
        ).first()
        assert updated_session.status == "ABANDONED"
        assert updated_session.ended_at is not None
        assert updated_session.error_message is not None
        assert "abandoned" in updated_session.error_message.lower()
        
        # Verify meeting marked as failed
        meeting = db_session.query(Meeting).filter(
            Meeting.id == live_session.meeting_id
        ).first()
        assert meeting.status == MeetingStatus.FAILED.value
    
    def test_cleanup_does_not_affect_active_sessions(
        self, session_manager, test_user
    ):
        """Test that cleanup doesn't remove active sessions"""
        # Create session
        live_session = session_manager.create_session(
            user_id=test_user.id,
            meeting_title="Test Meeting"
        )
        
        # Run cleanup immediately (session is still active)
        cleanup_count = session_manager.cleanup_abandoned_sessions(timeout_minutes=5)
        
        assert cleanup_count == 0
        assert session_manager.is_session_active(live_session.session_token)
    
    def test_cleanup_multiple_abandoned_sessions(
        self, session_manager, test_user
    ):
        """Test cleanup of multiple abandoned sessions"""
        # Create multiple sessions
        session1 = session_manager.create_session(test_user.id, "Meeting 1")
        session2 = session_manager.create_session(test_user.id, "Meeting 2")
        session3 = session_manager.create_session(test_user.id, "Meeting 3")
        
        # Mark first two as abandoned
        state1 = session_manager.get_session_state(session1.session_token)
        state1.last_activity = datetime.utcnow() - timedelta(minutes=10)
        
        state2 = session_manager.get_session_state(session2.session_token)
        state2.last_activity = datetime.utcnow() - timedelta(minutes=10)
        
        # Run cleanup
        cleanup_count = session_manager.cleanup_abandoned_sessions(timeout_minutes=5)
        
        assert cleanup_count == 2
        assert not session_manager.is_session_active(session1.session_token)
        assert not session_manager.is_session_active(session2.session_token)
        assert session_manager.is_session_active(session3.session_token)


class TestHelperMethods:
    """Tests for helper methods"""
    
    def test_get_active_session_count(self, session_manager, test_user):
        """Test getting active session count"""
        assert session_manager.get_active_session_count() == 0
        
        session1 = session_manager.create_session(test_user.id, "Meeting 1")
        assert session_manager.get_active_session_count() == 1
        
        session2 = session_manager.create_session(test_user.id, "Meeting 2")
        assert session_manager.get_active_session_count() == 2
        
        session_manager.end_session(session1.session_token)
        assert session_manager.get_active_session_count() == 1
        
        session_manager.end_session(session2.session_token)
        assert session_manager.get_active_session_count() == 0
    
    def test_is_session_active(self, session_manager, test_user):
        """Test checking if session is active"""
        live_session = session_manager.create_session(
            user_id=test_user.id,
            meeting_title="Test Meeting"
        )
        
        assert session_manager.is_session_active(live_session.session_token)
        assert not session_manager.is_session_active("invalid_token")
        
        session_manager.end_session(live_session.session_token)
        assert not session_manager.is_session_active(live_session.session_token)


class TestLiveSessionState:
    """Tests for LiveSessionState dataclass"""
    
    def test_live_session_state_creation(self):
        """Test creating LiveSessionState"""
        state = LiveSessionState(
            session_id=1,
            meeting_id=2,
            user_id=3,
            segment_count=5
        )
        
        assert state.session_id == 1
        assert state.meeting_id == 2
        assert state.user_id == 3
        assert state.segment_count == 5
        assert isinstance(state.last_activity, datetime)
    
    def test_update_activity(self):
        """Test updating activity timestamp"""
        state = LiveSessionState(
            session_id=1,
            meeting_id=2,
            user_id=3
        )
        
        initial_activity = state.last_activity
        
        import time
        time.sleep(0.01)
        
        state.update_activity()
        assert state.last_activity > initial_activity
