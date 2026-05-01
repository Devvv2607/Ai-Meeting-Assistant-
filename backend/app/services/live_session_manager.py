"""
Live Session Manager Service

Manages the lifecycle of live meeting sessions including creation, state tracking,
finalization, and cleanup of abandoned sessions.
"""

import logging
import secrets
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.models.meeting import Meeting, MeetingStatus
from app.models.live_session import LiveSession

logger = logging.getLogger(__name__)


# Module-level shared state for active sessions
# This persists across different LiveSessionManager instances
_active_sessions: Dict[str, "LiveSessionState"] = {}


@dataclass
class LiveSessionState:
    """In-memory state for an active live session"""
    session_id: int
    meeting_id: int
    user_id: int
    segment_count: int = 0
    last_activity: datetime = field(default_factory=datetime.utcnow)
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()


class LiveSessionManager:
    """
    Manages live meeting session lifecycle and state.
    
    Responsibilities:
    - Create new live sessions with Meeting and LiveSession records
    - Track active sessions in memory (shared across instances)
    - End sessions and finalize meeting data
    - Retrieve current session state
    - Clean up abandoned sessions
    """
    
    def __init__(self, db: Session):
        self.db = db
        # Use module-level shared state instead of instance-level
        self.active_sessions = _active_sessions
    
    def create_session(self, user_id: int, meeting_title: str) -> LiveSession:
        """
        Create a new live meeting session.
        
        Creates both a Meeting record and a LiveSession record, and tracks
        the session state in memory.
        
        Args:
            user_id: ID of the user creating the session
            meeting_title: Title for the meeting
            
        Returns:
            LiveSession: The created live session record
            
        Raises:
            Exception: If database operations fail
        """
        try:
            # Create meeting record
            meeting = Meeting(
                user_id=user_id,
                title=meeting_title,
                description="Live meeting capture",
                audio_url="live://stream",  # Placeholder for live sessions
                status=MeetingStatus.PROCESSING.value,
            )
            self.db.add(meeting)
            self.db.flush()  # Get meeting.id without committing
            
            # Create live session with secure token
            session_token = secrets.token_urlsafe(32)
            live_session = LiveSession(
                meeting_id=meeting.id,
                session_token=session_token,
                status="ACTIVE",
                started_at=datetime.utcnow()
            )
            self.db.add(live_session)
            self.db.commit()
            self.db.refresh(live_session)
            
            # Track in memory
            self.active_sessions[session_token] = LiveSessionState(
                session_id=live_session.id,
                meeting_id=meeting.id,
                user_id=user_id,
                segment_count=0
            )
            
            logger.info(
                f"Created live session {live_session.id} for meeting {meeting.id} "
                f"(user {user_id})"
            )
            
            return live_session
            
        except Exception as e:
            logger.error(f"Error creating live session: {str(e)}")
            self.db.rollback()
            raise
    
    def end_session(self, session_token: str) -> Meeting:
        """
        End a live meeting session and finalize the meeting.
        
        Updates the LiveSession status to ENDED, calculates duration,
        updates the Meeting status to COMPLETED, and cleans up in-memory state.
        
        Args:
            session_token: Token identifying the session to end
            
        Returns:
            Meeting: The finalized meeting record
            
        Raises:
            ValueError: If session token is invalid or session not found
            Exception: If database operations fail
        """
        try:
            # Get in-memory state
            state = self.active_sessions.get(session_token)
            if not state:
                raise ValueError(f"Session not found: {session_token}")
            
            # Get live session from database
            live_session = self.db.query(LiveSession).filter(
                LiveSession.session_token == session_token
            ).first()
            
            if not live_session:
                raise ValueError(f"LiveSession record not found: {session_token}")
            
            # Update live session status
            live_session.status = "ENDED"
            live_session.ended_at = datetime.utcnow()
            live_session.duration_seconds = (
                live_session.ended_at - live_session.started_at
            ).total_seconds()
            
            # Get and update meeting
            meeting = self.db.query(Meeting).filter(
                Meeting.id == state.meeting_id
            ).first()
            
            if not meeting:
                raise ValueError(f"Meeting not found: {state.meeting_id}")
            
            meeting.status = MeetingStatus.COMPLETED.value
            meeting.duration = live_session.duration_seconds
            
            self.db.commit()
            self.db.refresh(meeting)
            
            # Clean up from memory
            del self.active_sessions[session_token]
            
            logger.info(
                f"Ended live session {live_session.id} for meeting {meeting.id} "
                f"(duration: {live_session.duration_seconds:.1f}s)"
            )
            
            return meeting
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error ending live session: {str(e)}")
            self.db.rollback()
            raise
    
    def get_session_state(self, session_token: str) -> LiveSessionState:
        """
        Retrieve the current state of an active live session.
        
        Args:
            session_token: Token identifying the session
            
        Returns:
            LiveSessionState: Current state of the session
            
        Raises:
            ValueError: If session token is invalid or session not found
        """
        state = self.active_sessions.get(session_token)
        if not state:
            raise ValueError(f"Session not found: {session_token}")
        
        return state
    
    def update_segment_count(self, session_token: str, increment: int = 1):
        """
        Update the segment count for a session and refresh activity timestamp.
        
        Args:
            session_token: Token identifying the session
            increment: Number to increment segment count by (default: 1)
            
        Raises:
            ValueError: If session token is invalid
        """
        state = self.active_sessions.get(session_token)
        if not state:
            raise ValueError(f"Session not found: {session_token}")
        
        state.segment_count += increment
        state.update_activity()
    
    def cleanup_abandoned_sessions(self, timeout_minutes: int = 5):
        """
        Clean up sessions that have been inactive for too long.
        
        Marks sessions as ABANDONED if they haven't had activity within
        the timeout period. This prevents memory leaks from disconnected clients.
        
        Args:
            timeout_minutes: Minutes of inactivity before marking as abandoned
            
        Returns:
            int: Number of sessions cleaned up
        """
        try:
            timeout_threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
            abandoned_tokens = []
            
            # Find abandoned sessions
            for token, state in self.active_sessions.items():
                if state.last_activity < timeout_threshold:
                    abandoned_tokens.append(token)
            
            # Clean up each abandoned session
            cleanup_count = 0
            for token in abandoned_tokens:
                try:
                    state = self.active_sessions[token]
                    
                    # Update database record
                    live_session = self.db.query(LiveSession).filter(
                        LiveSession.session_token == token
                    ).first()
                    
                    if live_session:
                        live_session.status = "ABANDONED"
                        live_session.ended_at = datetime.utcnow()
                        live_session.duration_seconds = (
                            live_session.ended_at - live_session.started_at
                        ).total_seconds()
                        live_session.error_message = (
                            f"Session abandoned after {timeout_minutes} minutes "
                            f"of inactivity"
                        )
                        
                        # Update meeting status
                        meeting = self.db.query(Meeting).filter(
                            Meeting.id == state.meeting_id
                        ).first()
                        if meeting:
                            meeting.status = MeetingStatus.FAILED.value
                    
                    # Remove from memory
                    del self.active_sessions[token]
                    cleanup_count += 1
                    
                    logger.info(
                        f"Cleaned up abandoned session {state.session_id} "
                        f"(meeting {state.meeting_id})"
                    )
                    
                except Exception as e:
                    logger.error(
                        f"Error cleaning up session {token}: {str(e)}"
                    )
                    continue
            
            if cleanup_count > 0:
                self.db.commit()
                logger.info(f"Cleaned up {cleanup_count} abandoned sessions")
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Error in cleanup_abandoned_sessions: {str(e)}")
            self.db.rollback()
            return 0
    
    def get_active_session_count(self) -> int:
        """
        Get the number of currently active sessions.
        
        Returns:
            int: Number of active sessions in memory
        """
        return len(self.active_sessions)
    
    def is_session_active(self, session_token: str) -> bool:
        """
        Check if a session is currently active.
        
        Args:
            session_token: Token identifying the session
            
        Returns:
            bool: True if session is active, False otherwise
        """
        return session_token in self.active_sessions
