from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Header,
    Form,
)
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.user import User
from app.models.meeting import Meeting, MeetingStatus
from app.schemas.meeting_schema import (
    MeetingCreate,
    MeetingUpdate,
    MeetingResponse,
    MeetingListResponse,
)
from app.utils.auth_utils import verify_token
from app.utils.s3_utils import s3_service
from app.utils.audio_utils import AudioProcessor
from app.services.audio_processor import audio_processing_service
from app.config import settings
from app.models.transcript import Transcript
from app.models.summary import Summary
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/meetings", tags=["meetings"])


def get_current_user(
    authorization: str = Header(...), db: Session = Depends(get_db)
) -> User:
    """Get current user from JWT token

    Args:
        authorization: Authorization header
        db: Database session

    Returns:
        Current user
    """
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


@router.post("/upload", response_model=MeetingResponse)
async def upload_meeting(
    title: str = Form(...),
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload meeting audio file

    Args:
        title: Meeting title
        file: Audio file
        description: Optional meeting description
        current_user: Current user
        db: Database session

    Returns:
        Created meeting
    """
    temp_path = None
    try:
        # Validate file type
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in settings.ALLOWED_AUDIO_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format. Allowed: {', '.join(settings.ALLOWED_AUDIO_FORMATS)}",
            )

        # Validate file size
        contents = await file.read()
        if len(contents) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds maximum limit (2GB)",
            )

        # Save file temporarily - use system temp directory
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, file.filename)
        with open(temp_path, "wb") as f:
            f.write(contents)

        logger.info(f"Saved uploaded file to {temp_path}")

        # Get audio duration
        audio_processor = AudioProcessor()
        duration = audio_processor.get_duration(temp_path)

        # Upload to S3
        s3_key = f"meetings/{current_user.id}/{file.filename}"
        s3_url = s3_service.upload_file(temp_path, s3_key)

        if not s3_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to storage",
            )

        # Create meeting record
        meeting = Meeting(
            user_id=current_user.id,
            title=title,
            description=description,
            audio_url=s3_url,
            duration=duration,
            status=MeetingStatus.PENDING,
        )

        db.add(meeting)
        db.commit()
        db.refresh(meeting)

        logger.info(f"Created meeting {meeting.id} for user {current_user.id}")

        # Process meeting with real transcription
        try:
            meeting.status = MeetingStatus.PROCESSING
            db.commit()
            
            # Get local file path for processing
            if s3_url.startswith("local://"):
                local_key = s3_url.replace("local://", "")
                from pathlib import Path
                local_file_path = Path("backend/uploads") / local_key
                
                logger.info(f"Processing audio file: {local_file_path}")
                logger.info(f"File exists: {local_file_path.exists()}")
                
                if local_file_path.exists():
                    # Process the audio file
                    result = audio_processing_service.process_meeting(str(local_file_path), meeting.id)
                    
                    if result and result.get("transcripts"):
                        # Save transcripts to database
                        for segment in result["transcripts"]:
                            transcript = Transcript(
                                meeting_id=meeting.id,
                                speaker=segment.get("speaker", "Speaker 1"),
                                text=segment.get("text", ""),
                                start_time=float(segment.get("start_time", 0.0)),
                                end_time=float(segment.get("end_time", 0.0))
                            )
                            db.add(transcript)
                        
                        db.commit()
                        logger.info(f"Saved {len(result['transcripts'])} transcript segments for meeting {meeting.id}")
                        
                        meeting.status = MeetingStatus.COMPLETED
                        db.commit()
                    else:
                        logger.warning(f"No transcripts generated for meeting {meeting.id}")
                        meeting.status = MeetingStatus.COMPLETED
                        db.commit()
                else:
                    logger.error(f"Audio file not found at {local_file_path}")
                    meeting.status = MeetingStatus.FAILED
                    db.commit()
            else:
                # S3 file - mark as completed for now
                meeting.status = MeetingStatus.COMPLETED
                db.commit()
                
        except Exception as process_error:
            logger.error(f"Error processing meeting: {process_error}", exc_info=True)
            meeting.status = MeetingStatus.FAILED
            db.commit()

        return meeting

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading meeting: {e}")
        # Rollback database transaction on error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading meeting: {str(e)}",
        )
    finally:
        # Always clean up temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info(f"Cleaned up temporary file: {temp_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temp file {temp_path}: {cleanup_error}")


@router.get("", response_model=List[MeetingListResponse])
async def list_meetings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
):
    """List user's meetings

    Args:
        current_user: Current user
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of meetings
    """
    meetings = (
        db.query(Meeting)
        .filter(Meeting.user_id == current_user.id)
        .order_by(Meeting.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return meetings


@router.get("/{meeting_id}/summary")
async def get_summary(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get or generate meeting summary
    
    Args:
        meeting_id: Meeting ID
        current_user: Current user
        db: Database session
        
    Returns:
        Summary data
    """
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
    
    # Check if summary already exists
    existing_summary = db.query(Summary).filter(Summary.meeting_id == meeting_id).first()
    
    if existing_summary:
        logger.info(f"Returning existing summary for meeting {meeting_id}")
        return {
            "summary": existing_summary.summary_text,
            "key_points": existing_summary.key_points or [],
            "action_items": existing_summary.action_items or [],
            "sentiment": existing_summary.sentiment or "neutral"
        }
    
    # Generate new summary from transcripts
    try:
        logger.info(f"Generating summary for meeting {meeting_id}")
        
        # Get all transcripts for this meeting
        transcripts = db.query(Transcript).filter(Transcript.meeting_id == meeting_id).all()
        
        if not transcripts:
            logger.warning(f"No transcripts found for meeting {meeting_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No transcripts available for summary generation",
            )
        
        # Combine all transcript text
        full_text = " ".join([t.text for t in transcripts])
        
        # Generate summary using Groq LLM
        from app.services.summary_service import summary_service
        
        summary_data = summary_service.generate_summary(full_text)
        
        if summary_data:
            # Save summary to database
            new_summary = Summary(
                meeting_id=meeting_id,
                summary_text=summary_data.get("summary"),
                key_points=summary_data.get("key_points", []),
                action_items=summary_data.get("action_items", []),
                sentiment=summary_data.get("sentiment", "neutral")
            )
            db.add(new_summary)
            db.commit()
            
            logger.info(f"✓ Summary generated and saved for meeting {meeting_id}")
            
            return summary_data
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate summary",
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating summary for meeting {meeting_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating summary: {str(e)}",
        )


@router.get("/{meeting_id}/transcripts")
async def get_transcripts(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get meeting transcripts
    
    Args:
        meeting_id: Meeting ID
        current_user: Current user
        db: Database session
        
    Returns:
        List of transcript segments
    """
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
    transcripts = db.query(Transcript).filter(Transcript.meeting_id == meeting_id).all()
    
    return {
        "segments": [
            {
                "id": t.id,
                "speaker": t.speaker,
                "text": t.text,
                "start_time": t.start_time,
                "end_time": t.end_time
            }
            for t in transcripts
        ]
    }


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get meeting details

    Args:
        meeting_id: Meeting ID
        current_user: Current user
        db: Database session

    Returns:
        Meeting details
    """
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

    return meeting


@router.put("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: int,
    update_data: MeetingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update meeting

    Args:
        meeting_id: Meeting ID
        update_data: Update data
        current_user: Current user
        db: Database session

    Returns:
        Updated meeting
    """
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

    update_dict = update_data.dict(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(meeting, key, value)

    db.commit()
    db.refresh(meeting)

    return meeting


@router.delete("/{meeting_id}")
async def delete_meeting(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete meeting

    Args:
        meeting_id: Meeting ID
        current_user: Current user
        db: Database session

    Returns:
        Success message
    """
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

    # Delete from storage (S3 or local)
    if meeting.audio_url.startswith("s3://"):
        s3_key = meeting.audio_url.replace(f"s3://{settings.S3_BUCKET_NAME}/", "")
    elif meeting.audio_url.startswith("local://"):
        s3_key = meeting.audio_url.replace("local://", "")
    else:
        s3_key = meeting.audio_url
    
    s3_service.delete_file(s3_key)

    # Delete meeting
    db.delete(meeting)
    db.commit()

    logger.info(f"Deleted meeting {meeting_id}")

    return {"message": "Meeting deleted successfully"}
