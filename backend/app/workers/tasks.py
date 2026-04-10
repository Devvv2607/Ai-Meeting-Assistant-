from celery import current_task
from app.workers.celery_config import celery_app
from app.services.audio_processor import audio_processing_service
from app.services.llm_service import llm_service
from app.services.embedding_service import embedding_service
from app.database import SessionLocal
from app.models.meeting import Meeting, MeetingStatus
from app.models.transcript import Transcript
from app.models.summary import Summary
from app.utils.s3_utils import s3_service
import logging
import os

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="process_meeting")
def process_meeting_task(self, meeting_id: int, audio_s3_path: str):
    """Celery task to process meeting audio

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

        logger.info(f"Starting processing for meeting {meeting_id}")

        # Step 1: Download audio from S3
        local_audio_path = f"/tmp/meeting_{meeting_id}_audio.wav"
        s3_key = audio_s3_path.replace("s3://ai-meeting-bucket/", "")

        success = s3_service.download_file(s3_key, local_audio_path)
        if not success:
            raise Exception("Failed to download audio from S3")

        # Update progress
        current_task.update_state(state="PROGRESS", meta={"stage": "downloading", "progress": 10})
        logger.info(f"Downloaded audio to {local_audio_path}")

        # Step 2: Process audio
        result = audio_processing_service.process_meeting(local_audio_path, meeting_id)
        if not result:
            raise Exception("Failed to process audio")

        current_task.update_state(state="PROGRESS", meta={"stage": "transcribing", "progress": 50})
        logger.info(f"Audio processing completed for meeting {meeting_id}")

        # Step 3: Store transcripts in database
        transcripts = result.get("transcripts", [])
        embeddings = result.get("embeddings", [])

        for i, transcript in enumerate(transcripts):
            embedding_data = None
            if i < len(embeddings):
                import json

                embedding_data = json.dumps(embeddings[i]).encode()

            db_transcript = Transcript(
                meeting_id=meeting_id,
                speaker=transcript.get("speaker", "Unknown"),
                text=transcript.get("text", ""),
                start_time=transcript.get("start", 0),
                end_time=transcript.get("end", 0),
                embedding=embedding_data,
            )
            db.add(db_transcript)

        db.commit()
        current_task.update_state(state="PROGRESS", meta={"stage": "storing_transcripts", "progress": 70})
        logger.info(f"Stored {len(transcripts)} transcript segments")

        # Step 4: Generate AI summary
        full_transcript = " ".join([t.get("text", "") for t in transcripts])
        summary_result = llm_service.generate_summary(full_transcript)

        if summary_result:
            summary = Summary(
                meeting_id=meeting_id,
                summary=summary_result.get("summary", ""),
                key_points=summary_result.get("key_points", []),
                action_items=summary_result.get("action_items", []),
                sentiment=summary_result.get("sentiment", ""),
            )
            db.add(summary)
            db.commit()
            logger.info(f"Summary generated for meeting {meeting_id}")

        current_task.update_state(state="PROGRESS", meta={"stage": "generating_summary", "progress": 90})

        # Step 5: Update meeting status
        meeting.status = MeetingStatus.COMPLETED
        meeting.duration = result.get("duration", 0)
        db.commit()

        # Clean up local file
        if os.path.exists(local_audio_path):
            os.remove(local_audio_path)

        logger.info(f"Meeting {meeting_id} processing completed successfully")
        return {"status": "success", "meeting_id": meeting_id}

    except Exception as e:
        logger.error(f"Error processing meeting {meeting_id}: {e}")

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
    """Celery task to regenerate summary for a meeting

    Args:
        meeting_id: ID of the meeting
    """
    db = SessionLocal()

    try:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            logger.error(f"Meeting {meeting_id} not found")
            return {"status": "failed", "reason": "Meeting not found"}

        # Get all transcripts
        transcripts = db.query(Transcript).filter(Transcript.meeting_id == meeting_id).all()
        full_transcript = " ".join([t.text for t in transcripts])

        # Generate new summary
        summary_result = llm_service.generate_summary(full_transcript)

        if summary_result:
            summary = db.query(Summary).filter(Summary.meeting_id == meeting_id).first()
            if summary:
                summary.summary = summary_result.get("summary", "")
                summary.key_points = summary_result.get("key_points", [])
                summary.action_items = summary_result.get("action_items", [])
                summary.sentiment = summary_result.get("sentiment", "")
            else:
                summary = Summary(
                    meeting_id=meeting_id,
                    summary=summary_result.get("summary", ""),
                    key_points=summary_result.get("key_points", []),
                    action_items=summary_result.get("action_items", []),
                    sentiment=summary_result.get("sentiment", ""),
                )
                db.add(summary)

            db.commit()
            logger.info(f"Summary regenerated for meeting {meeting_id}")
            return {"status": "success", "meeting_id": meeting_id}

        return {"status": "failed", "reason": "Failed to generate summary"}

    except Exception as e:
        logger.error(f"Error regenerating summary for meeting {meeting_id}: {e}")
        return {"status": "failed", "reason": str(e)}

    finally:
        db.close()
