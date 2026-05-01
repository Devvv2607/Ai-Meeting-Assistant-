import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.auth_utils import get_current_user
from app.models.user import User
from app.models.live_session import LiveSession
from app.models.speaker import Speaker
from app.services.live_session_manager import LiveSessionManager
from app.services.live_audio_processor import LiveAudioProcessor
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/meetings", tags=["live-meetings"])


@router.post("/start-live")
async def start_live_meeting(
    meeting_title: str = Query(..., description="Title for the live meeting"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Start a new live meeting session.
    
    Creates a new Meeting record and LiveSession record, generates a secure
    session token, and returns the WebSocket URL for audio streaming.
    
    Args:
        meeting_title: Title for the meeting
        current_user: Authenticated user (from JWT token)
        db: Database session
        
    Returns:
        dict: Contains meeting_id, session_token, and websocket_url
        
    Raises:
        HTTPException: If session creation fails
    """
    try:
        manager = LiveSessionManager(db)
        live_session = manager.create_session(current_user.id, meeting_title)
        
        # Construct WebSocket URL
        # Client will need to construct this based on their backend URL
        # For now, return a relative path that the frontend can use
        websocket_url = f"/ws/live/{live_session.session_token}"
        
        logger.info(
            f"Started live meeting {live_session.meeting_id} for user {current_user.id}"
        )
        
        return {
            "meeting_id": live_session.meeting_id,
            "session_token": live_session.session_token,
            "websocket_url": websocket_url,
            "status": "ACTIVE"
        }
        
    except Exception as e:
        logger.error(f"Error starting live meeting: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start live meeting: {str(e)}",
        )


@router.post("/{meeting_id}/end")
async def end_live_meeting(
    meeting_id: int,
    session_token: str = Query(..., description="Session token from start-live"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    End a live meeting session and finalize the meeting.
    
    Updates the LiveSession status to ENDED, calculates duration,
    updates the Meeting status to COMPLETED, and triggers audio processing
    (transcription, speaker diarization, summary generation).
    
    Args:
        meeting_id: ID of the meeting to end
        session_token: Session token from start-live endpoint
        current_user: Authenticated user (from JWT token)
        db: Database session
        background_tasks: FastAPI background tasks
        
    Returns:
        dict: Contains meeting_id, status, duration, and processing status
        
    Raises:
        HTTPException: If session not found or meeting ID mismatch
    """
    try:
        manager = LiveSessionManager(db)
        audio_processor = LiveAudioProcessor(db)
        
        # Verify session exists and belongs to the meeting
        live_session = db.query(LiveSession).filter(
            LiveSession.session_token == session_token
        ).first()
        
        if not live_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if live_session.meeting_id != meeting_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Meeting ID does not match session"
            )
        
        # Verify user owns the meeting
        if live_session.meeting.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to end this meeting"
            )
        
        # Get audio stats before ending
        audio_stats = audio_processor.get_session_stats(session_token)
        
        logger.info(
            f"Ending meeting {meeting_id}: "
            f"{audio_stats['chunk_count']} chunks, "
            f"{audio_stats['total_bytes']} bytes"
        )
        
        # End the session (updates database status)
        meeting = manager.end_session(session_token)
        
        # Process audio in the foreground (synchronously)
        # This ensures transcription is complete before returning
        logger.info(f"Processing audio for meeting {meeting_id}")
        
        processing_result = audio_processor.process_meeting_audio(
            session_token,
            meeting_id
        )
        
        if not processing_result["success"]:
            logger.error(
                f"Audio processing failed for meeting {meeting_id}: "
                f"{processing_result.get('error')}"
            )
            # Don't fail the endpoint, just log the error
        else:
            logger.info(
                f"Audio processing complete for meeting {meeting_id}: "
                f"{processing_result['transcript_count']} transcripts, "
                f"{processing_result['speakers']} speakers"
            )
        
        return {
            "meeting_id": meeting.id,
            "status": meeting.status,
            "duration": meeting.duration,
            "audio_chunks": audio_stats['chunk_count'],
            "audio_bytes": audio_stats['total_bytes'],
            "processing": processing_result,
            "insights_ready": processing_result["success"]
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error ending live meeting: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end live meeting: {str(e)}",
        )


@router.get("/{meeting_id}/live-status")
async def get_live_status(
    meeting_id: int,
    session_token: str = Query(..., description="Session token from start-live"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the current status of a live meeting session.
    
    Returns session status, duration, segment count, and speaker information.
    
    Args:
        meeting_id: ID of the meeting
        session_token: Session token from start-live endpoint
        current_user: Authenticated user (from JWT token)
        db: Database session
        
    Returns:
        dict: Contains status, duration, segment_count, and speakers list
        
    Raises:
        HTTPException: If session not found or not authorized
    """
    try:
        manager = LiveSessionManager(db)
        
        # Verify session exists and belongs to the meeting
        live_session = db.query(LiveSession).filter(
            LiveSession.session_token == session_token
        ).first()
        
        if not live_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if live_session.meeting_id != meeting_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Meeting ID does not match session"
            )
        
        # Verify user owns the meeting
        if live_session.meeting.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this meeting"
            )
        
        # Get session state from memory
        state = manager.get_session_state(session_token)
        
        # Get speakers from database
        speakers = db.query(Speaker).filter(
            Speaker.meeting_id == meeting_id
        ).all()
        
        speaker_list = [
            {
                "speaker_number": s.speaker_number,
                "speaker_name": s.speaker_name or f"Speaker {s.speaker_number}",
                "talk_time_seconds": s.talk_time_seconds or 0,
                "word_count": s.word_count or 0
            }
            for s in speakers
        ]
        
        # Calculate duration
        from datetime import datetime
        duration_seconds = (
            datetime.utcnow() - live_session.started_at
        ).total_seconds()
        
        return {
            "status": live_session.status,
            "duration_seconds": duration_seconds,
            "segment_count": state.segment_count,
            "speakers": speaker_list,
            "meeting_id": meeting_id,
            "session_token": session_token
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting live status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get live status: {str(e)}",
        )
