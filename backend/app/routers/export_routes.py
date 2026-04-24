"""Routes for exporting meeting data (PDF, etc.)"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO
from app.database import get_db
from app.models.user import User
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.utils.auth_utils import verify_token
from app.services.pdf_service import pdf_service
from app.services.translation_service import translation_service, SUPPORTED_LANGUAGES
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["export"])


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


@router.get("/meetings/{meeting_id}/transcript/pdf")
async def download_transcript_pdf(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download meeting transcript as PDF
    
    Args:
        meeting_id: Meeting ID
        current_user: Current user
        db: Database session
        
    Returns:
        PDF file
    """
    try:
        # Verify meeting belongs to user
        meeting = (
            db.query(Meeting)
            .filter(Meeting.id == meeting_id, Meeting.user_id == current_user.id)
            .first()
        )
        
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found",
            )
        
        # Get transcripts
        transcripts = (
            db.query(Transcript)
            .filter(Transcript.meeting_id == meeting_id)
            .order_by(Transcript.start_time)
            .all()
        )
        
        if not transcripts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No transcripts available for this meeting",
            )
        
        logger.info(f"Generating PDF for meeting {meeting_id}")
        
        # Generate PDF
        pdf_bytes = pdf_service.generate_transcript_pdf(meeting, transcripts)
        
        # Create filename
        date_str = meeting.created_at.strftime("%Y%m%d") if meeting.created_at else "unknown"
        filename = f"{meeting.title.replace(' ', '_')}_{date_str}.pdf"
        
        logger.info(f"✓ PDF generated: {filename}")
        
        # Return PDF as bytes using StreamingResponse
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating PDF: {str(e)}",
        )


@router.post("/meetings/{meeting_id}/transcript/translate")
async def translate_transcript(
    meeting_id: int,
    request_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Translate meeting transcript to target language
    
    Args:
        meeting_id: Meeting ID
        request_data: {"target_language": "es"}
        current_user: Current user
        db: Database session
        
    Returns:
        Translated transcript segments
    """
    try:
        # Verify meeting belongs to user
        meeting = (
            db.query(Meeting)
            .filter(Meeting.id == meeting_id, Meeting.user_id == current_user.id)
            .first()
        )
        
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found",
            )
        
        # Get target language
        target_language = request_data.get("target_language", "en").lower()
        
        if target_language not in SUPPORTED_LANGUAGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported language: {target_language}. Supported: {', '.join(SUPPORTED_LANGUAGES.keys())}",
            )
        
        # Get transcripts
        transcripts = (
            db.query(Transcript)
            .filter(Transcript.meeting_id == meeting_id)
            .order_by(Transcript.start_time)
            .all()
        )
        
        if not transcripts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No transcripts available for this meeting",
            )
        
        logger.info(f"Translating meeting {meeting_id} to {target_language}")
        
        # Translate transcript
        result = translation_service.translate_transcript(
            transcripts,
            target_language
        )
        
        logger.info(f"✓ Translation complete for meeting {meeting_id}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error translating transcript: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error translating transcript: {str(e)}",
        )


@router.get("/languages")
async def get_supported_languages():
    """Get list of supported languages
    
    Returns:
        Dictionary of supported languages
    """
    return {
        "languages": SUPPORTED_LANGUAGES,
        "count": len(SUPPORTED_LANGUAGES)
    }
