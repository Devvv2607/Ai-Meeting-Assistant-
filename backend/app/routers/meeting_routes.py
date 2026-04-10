from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Header,
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
from app.config import settings
from app.workers.tasks import process_meeting_task
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
    title: str,
    file: UploadFile = File(...),
    description: Optional[str] = None,
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

        # Save file temporarily
        temp_path = f"/tmp/{file.filename}"
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

        # Trigger async processing
        task = process_meeting_task.delay(meeting.id, s3_url)
        meeting.celery_task_id = task.id
        db.commit()

        logger.info(f"Triggered async processing task {task.id} for meeting {meeting.id}")

        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

        return meeting

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading meeting: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading meeting: {str(e)}",
        )


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

    # Delete from S3
    s3_key = meeting.audio_url.replace("s3://ai-meeting-bucket/", "")
    s3_service.delete_file(s3_key)

    # Delete meeting
    db.delete(meeting)
    db.commit()

    logger.info(f"Deleted meeting {meeting_id}")

    return {"message": "Meeting deleted successfully"}
