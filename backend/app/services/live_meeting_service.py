import logging
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.meeting import Meeting, MeetingStatus
from app.models.live_session import LiveSession
from app.models.transcript import Transcript
from app.models.speaker import Speaker
from app.services.whisper_service import WhisperService
from app.services.summary_service import SummaryService

logger = logging.getLogger(__name__)


class LiveMeetingService:
    """Service for managing live meeting sessions"""

    def __init__(self, db: Session):
        self.db = db
        self.whisper_service = WhisperService()
        self.summary_service = SummaryService()
        self.active_sessions = {}  # In-memory store for active sessions

    def create_live_session(self, user_id: int, meeting_title: str) -> dict:
        """Create a new live meeting session"""
        try:
            # Create meeting record
            meeting = Meeting(
                user_id=user_id,
                title=meeting_title,
                description="Live meeting capture",
                audio_url="live://stream",
                status=MeetingStatus.PROCESSING.value,
            )
            self.db.add(meeting)
            self.db.commit()
            self.db.refresh(meeting)

            # Create live session
            session_token = str(uuid.uuid4())
            live_session = LiveSession(
                meeting_id=meeting.id,
                session_token=session_token,
                status="ACTIVE",
            )
            self.db.add(live_session)
            self.db.commit()
            self.db.refresh(live_session)

            # Store in memory
            self.active_sessions[session_token] = {
                "meeting_id": meeting.id,
                "live_session_id": live_session.id,
                "transcripts": [],
                "speakers": {},
                "started_at": datetime.utcnow(),
            }

            logger.info(f"Created live session {session_token} for meeting {meeting.id}")

            return {
                "meeting_id": meeting.id,
                "session_token": session_token,
                "status": "ACTIVE",
            }
        except Exception as e:
            logger.error(f"Error creating live session: {str(e)}")
            self.db.rollback()
            raise

    def process_audio_chunk(
        self, session_token: str, audio_data: bytes
    ) -> dict:
        """Process an audio chunk from live meeting"""
        try:
            if session_token not in self.active_sessions:
                raise ValueError(f"Invalid session token: {session_token}")

            session = self.active_sessions[session_token]

            # Transcribe audio chunk
            transcription = self.whisper_service.transcribe_audio(audio_data)

            if not transcription or not transcription.get("text"):
                return {"text": "", "speaker": "Unknown"}

            # Extract speaker info (simplified - would use pyannote.audio in production)
            speaker_label = self._detect_speaker(session, transcription)

            # Store transcript
            transcript_data = {
                "text": transcription.get("text", ""),
                "speaker": speaker_label,
                "language": transcription.get("language", "en"),
                "timestamp": datetime.utcnow().isoformat(),
            }

            session["transcripts"].append(transcript_data)

            logger.info(
                f"Processed chunk for session {session_token}: {speaker_label}"
            )

            return transcript_data

        except Exception as e:
            logger.error(f"Error processing audio chunk: {str(e)}")
            raise

    def _detect_speaker(self, session: dict, transcription: dict) -> str:
        """Detect speaker from transcription (simplified)"""
        # In production, use pyannote.audio for accurate speaker diarization
        # For now, use a simple heuristic based on voice characteristics
        speakers = session.get("speakers", {})

        # Simplified: alternate between speakers or detect based on audio features
        if not speakers:
            speaker_num = 1
        else:
            speaker_num = len(speakers) + 1

        speaker_label = f"Speaker {speaker_num}"
        speakers[speaker_num] = {"name": speaker_label, "segments": 1}

        return speaker_label

    def end_live_session(self, session_token: str) -> dict:
        """End a live meeting session and generate transcript"""
        try:
            if session_token not in self.active_sessions:
                raise ValueError(f"Invalid session token: {session_token}")

            session = self.active_sessions[session_token]
            meeting_id = session["meeting_id"]

            # Get meeting from database
            meeting = self.db.query(Meeting).filter(Meeting.id == meeting_id).first()
            if not meeting:
                raise ValueError(f"Meeting not found: {meeting_id}")

            # Store all transcripts in database
            for i, transcript_data in enumerate(session["transcripts"]):
                transcript = Transcript(
                    meeting_id=meeting_id,
                    text=transcript_data["text"],
                    speaker_name=transcript_data["speaker"],
                    language=transcript_data.get("language", "en"),
                    start_time=i * 3,  # Approximate timing
                    end_time=(i + 1) * 3,
                )
                self.db.add(transcript)

            # Create speakers
            for speaker_num, speaker_info in session["speakers"].items():
                speaker = Speaker(
                    meeting_id=meeting_id,
                    speaker_number=speaker_num,
                    speaker_name=speaker_info["name"],
                )
                self.db.add(speaker)

            # Update meeting status
            meeting.status = MeetingStatus.COMPLETED.value
            meeting.duration = (
                datetime.utcnow() - session["started_at"]
            ).total_seconds()

            # Update live session
            live_session = (
                self.db.query(LiveSession)
                .filter(LiveSession.session_token == session_token)
                .first()
            )
            if live_session:
                live_session.status = "ENDED"
                live_session.ended_at = datetime.utcnow()
                live_session.duration_seconds = meeting.duration

            self.db.commit()

            # Generate summary
            full_transcript = "\n".join(
                [f"{t['speaker']}: {t['text']}" for t in session["transcripts"]]
            )
            summary = self.summary_service.generate_summary(full_transcript)

            # Clean up from memory
            del self.active_sessions[session_token]

            logger.info(f"Ended live session {session_token} for meeting {meeting_id}")

            return {
                "meeting_id": meeting_id,
                "status": "COMPLETED",
                "duration": meeting.duration,
                "transcript_count": len(session["transcripts"]),
                "speakers": len(session["speakers"]),
                "summary": summary,
            }

        except Exception as e:
            logger.error(f"Error ending live session: {str(e)}")
            self.db.rollback()
            raise

    def get_session_status(self, session_token: str) -> dict:
        """Get current status of a live session"""
        if session_token not in self.active_sessions:
            raise ValueError(f"Invalid session token: {session_token}")

        session = self.active_sessions[session_token]
        return {
            "session_token": session_token,
            "meeting_id": session["meeting_id"],
            "transcript_count": len(session["transcripts"]),
            "speakers": len(session["speakers"]),
            "duration": (
                datetime.utcnow() - session["started_at"]
            ).total_seconds(),
        }
