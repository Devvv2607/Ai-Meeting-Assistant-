from celery import current_task
from app.workers.celery_config import celery_app
from app.services.audio_processor import audio_processing_service
from app.database import SessionLocal
from app.models.meeting import Meeting, MeetingStatus
from app.models.transcript import Transcript
from app.models.summary import Summary
from app.utils.s3_utils import s3_service
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="process_meeting")
def process_meeting_task(self, meeting_id: int, audio_s3_path: str):
    """Celery task to process meeting audio with real transcription

    Args:
        meeting_id: ID of the meeting
        audio_s3_path: S3 path to audio file
    """
    db = SessionLocal()

    try:
        # Update meeting status to processing
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            logger.error(f"Meeting {meeting_id} not found")
            return {"status": "failed", "reason": "Meeting not found"}

        meeting.status = MeetingStatus.PROCESSING
        meeting.celery_task_id = self.request.id
        db.commit()

        logger.info(f"Processing meeting {meeting_id} with real transcription")

        # Get local file path for processing
        if audio_s3_path.startswith("local://"):
            local_key = audio_s3_path.replace("local://", "")
            local_file_path = Path("backend/uploads") / local_key
            
            logger.info(f"Processing audio file: {local_file_path}")
            
            # Process the audio file with real transcription
            result = audio_processing_service.process_meeting(str(local_file_path), meeting_id)
            
            if result and result.get("transcripts"):
                # Save transcripts to database
                for segment in result["transcripts"]:
                    transcript = Transcript(
                        meeting_id=meeting_id,
                        speaker=segment.get("speaker", "Speaker 1"),
                        text=segment.get("text", ""),
                        start_time=float(segment.get("start_time", 0.0)),
                        end_time=float(segment.get("end_time", 0.0))
                    )
                    db.add(transcript)
                
                db.commit()
                logger.info(f"Saved {len(result['transcripts'])} transcript segments for meeting {meeting_id}")
                
                meeting.status = MeetingStatus.COMPLETED
                db.commit()
                
                return {"status": "success", "meeting_id": meeting_id, "segments": len(result["transcripts"])}
            else:
                logger.warning(f"No transcripts generated for meeting {meeting_id}")
                meeting.status = MeetingStatus.COMPLETED
                db.commit()
                return {"status": "success", "meeting_id": meeting_id, "segments": 0}
        else:
            logger.warning(f"S3 files not supported yet for meeting {meeting_id}")
            meeting.status = MeetingStatus.COMPLETED
            db.commit()
            return {"status": "success", "meeting_id": meeting_id, "note": "s3_not_supported"}

    except Exception as e:
        logger.error(f"Error processing meeting {meeting_id}: {e}", exc_info=True)

        # Update meeting status to failed
        try:
            meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
            if meeting:
                meeting.status = MeetingStatus.FAILED
                db.commit()
        except Exception as db_error:
            logger.error(f"Error updating meeting status: {db_error}")

        return {"status": "failed", "reason": str(e)}

    finally:
        db.close()


@celery_app.task(bind=True, name="regenerate_summary")
def regenerate_summary_task(self, meeting_id: int):
    """Celery task to regenerate summary

    Args:
        meeting_id: ID of the meeting
    """
    db = SessionLocal()
    
    try:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            logger.error(f"Meeting {meeting_id} not found")
            return {"status": "failed", "reason": "Meeting not found"}
        
        logger.info(f"Regenerating summary for meeting {meeting_id}")
        
        # Get transcripts
        transcripts = db.query(Transcript).filter(Transcript.meeting_id == meeting_id).all()
        
        if not transcripts:
            logger.warning(f"No transcripts found for meeting {meeting_id}")
            return {"status": "failed", "reason": "No transcripts available"}
        
        # Combine all transcript text
        full_text = " ".join([t.text for t in transcripts])
        
        # For now, just create a placeholder summary
        # In production, this would call an LLM service
        summary_text = f"Summary of {len(transcripts)} segments: {full_text[:500]}..."
        
        # Save or update summary
        summary = db.query(Summary).filter(Summary.meeting_id == meeting_id).first()
        if summary:
            summary.summary_text = summary_text
        else:
            summary = Summary(
                meeting_id=meeting_id,
                summary_text=summary_text
            )
            db.add(summary)
        
        db.commit()
        logger.info(f"Summary regenerated for meeting {meeting_id}")
        
        return {"status": "success", "meeting_id": meeting_id}
        
    except Exception as e:
        logger.error(f"Error regenerating summary for meeting {meeting_id}: {e}", exc_info=True)
        return {"status": "failed", "reason": str(e)}
    finally:
        db.close()
