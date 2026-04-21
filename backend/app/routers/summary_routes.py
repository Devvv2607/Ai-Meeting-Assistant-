"""Summary and insights routes"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.meeting import Meeting
from app.models.summary import Summary
from app.utils.auth_utils import verify_token
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["summaries"])


def get_current_user(
    authorization: str = Header(...), db: Session = Depends(get_db)
) -> User:
    """Get current user from JWT token"""
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid scheme")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


@router.get("/insights")
async def get_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get system insights and statistics
    
    Args:
        current_user: Current user
        db: Database session
        
    Returns:
        System insights including status, configuration, and performance metrics
    """
    try:
        # Get user's meetings
        meetings = db.query(Meeting).filter(Meeting.user_id == current_user.id).all()
        
        # Calculate statistics
        total_meetings = len(meetings)
        completed_meetings = len([m for m in meetings if m.status == "completed"])
        failed_meetings = len([m for m in meetings if m.status == "failed"])
        processing_meetings = len([m for m in meetings if m.status == "processing"])
        
        # Calculate total duration
        total_duration = sum([m.duration or 0 for m in meetings])
        avg_duration = total_duration / total_meetings if total_meetings > 0 else 0
        
        # Get summaries count
        summaries = db.query(Summary).filter(
            Summary.meeting_id.in_([m.id for m in meetings])
        ).all()
        
        logger.info(f"Generated insights for user {current_user.id}")
        
        return {
            "systemStatus": {
                "backend": "✅ Running",
                "database": "✅ Connected",
                "groqApi": "✅ Active",
            },
            "configuration": {
                "provider": "Groq",
                "model": settings.LLM_MODEL,
                "environment": "venv_local (Python 3.10+)",
            },
            "performance": {
                "avgTranscriptionTime": int(avg_duration),
                "avgFileSize": 1.42,  # MB - placeholder
                "totalProcessed": total_meetings,
                "completedMeetings": completed_meetings,
                "failedMeetings": failed_meetings,
                "processingMeetings": processing_meetings,
            },
            "features": [
                "User Authentication (JWT)",
                "Audio File Upload (MP3, WAV, M4A, MP4)",
                "Groq Whisper Transcription",
                "Real-time Transcript Storage",
                "Meeting Management (CRUD)",
                "Frontend-Backend Integration",
                "Error Handling & Fallbacks",
                "Database Persistence",
                "AI-Powered Summaries",
                "Sentiment Analysis",
            ],
            "technicalStack": {
                "frontend": "Next.js 14.2.35 (TypeScript/React)",
                "backend": "FastAPI + Uvicorn",
                "database": "PostgreSQL 15",
                "ai": f"Groq API ({settings.LLM_MODEL})",
            },
            "statistics": {
                "totalMeetings": total_meetings,
                "completedMeetings": completed_meetings,
                "failedMeetings": failed_meetings,
                "processingMeetings": processing_meetings,
                "totalDuration": int(total_duration),
                "averageDuration": int(avg_duration),
                "summariesGenerated": len(summaries),
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating insights: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating insights: {str(e)}",
        )
