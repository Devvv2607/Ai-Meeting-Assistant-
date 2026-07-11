"""
Live Audio Processor Service

Handles real-time audio chunk storage and post-meeting processing
for live meeting sessions.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from pydub import AudioSegment
from sqlalchemy.orm import Session

from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.speaker import Speaker
from app.services.whisper_service import WhisperService
from app.services.summary_service import SummaryService

logger = logging.getLogger(__name__)


# Module-level shared state for audio chunks
# This persists across different LiveAudioProcessor instances
_audio_chunks: dict[str, List[bytes]] = {}


class LiveAudioProcessor:
    """
    Processes audio chunks from live meetings.
    
    Responsibilities:
    - Store audio chunks during meeting
    - Combine chunks into single audio file
    - Transcribe audio after meeting ends
    - Apply speaker diarization
    - Generate meeting summary
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.whisper_service = WhisperService()
        self.summary_service = SummaryService()
        
        # Use module-level shared state instead of instance-level
        self.audio_chunks = _audio_chunks
        
        # Create temp directory for audio files
        self.temp_dir = Path(tempfile.gettempdir()) / "live_meetings"
        self.temp_dir.mkdir(exist_ok=True)
    
    def store_audio_chunk(self, session_token: str, audio_data: bytes) -> None:
        """
        Store an audio chunk for a live session.
        
        Args:
            session_token: Session identifier
            audio_data: Raw audio bytes from MediaRecorder
        """
        try:
            if session_token not in self.audio_chunks:
                self.audio_chunks[session_token] = []
            
            self.audio_chunks[session_token].append(audio_data)
            
            logger.debug(
                f"Stored audio chunk for session {session_token}: "
                f"{len(audio_data)} bytes "
                f"(total chunks: {len(self.audio_chunks[session_token])})"
            )
            
        except Exception as e:
            logger.error(f"Error storing audio chunk: {str(e)}")
            raise
    
    def get_chunk_count(self, session_token: str) -> int:
        """Get the number of stored chunks for a session."""
        return len(self.audio_chunks.get(session_token, []))
    
    def _combine_audio_chunks(self, session_token: str) -> Optional[str]:
        """
        Combine all audio chunks into a single audio file.
        
        Args:
            session_token: Session identifier
            
        Returns:
            str: Path to the combined audio file, or None if no chunks
        """
        try:
            chunks = self.audio_chunks.get(session_token, [])
            
            if not chunks:
                logger.warning(f"No audio chunks found for session {session_token}")
                return None
            
            logger.info(
                f"Combining {len(chunks)} audio chunks for session {session_token}"
            )
            
            # Create output file path
            output_path = self.temp_dir / f"{session_token}.webm"
            
            # Write all chunks to a single file
            with open(output_path, 'wb') as f:
                for chunk in chunks:
                    f.write(chunk)
            
            file_size = os.path.getsize(output_path)
            logger.info(
                f"Combined audio file created: {output_path} ({file_size} bytes)"
            )
            
            # Convert to WAV for better compatibility with Whisper
            try:
                audio = AudioSegment.from_file(output_path, format="webm")
                wav_path = self.temp_dir / f"{session_token}.wav"
                audio.export(wav_path, format="wav")
                
                logger.info(f"Converted to WAV: {wav_path}")
                
                # Clean up webm file
                os.remove(output_path)
                
                return str(wav_path)
                
            except Exception as e:
                logger.warning(f"Failed to convert to WAV: {str(e)}, using webm")
                return str(output_path)
            
        except Exception as e:
            logger.error(f"Error combining audio chunks: {str(e)}")
            raise
    
    def process_meeting_audio(
        self,
        session_token: str,
        meeting_id: int
    ) -> dict:
        """
        Process all audio from a completed meeting.
        
        This is called when a meeting ends. It:
        1. Combines audio chunks into a single file
        2. Transcribes the audio
        3. Applies speaker diarization
        4. Generates summary
        5. Stores everything in database
        
        Args:
            session_token: Session identifier
            meeting_id: Meeting ID
            
        Returns:
            dict: Processing results with transcript count, speakers, etc.
        """
        try:
            logger.info(
                f"Starting audio processing for meeting {meeting_id} "
                f"(session {session_token})"
            )

            # Ensure the live recording is a finalized WAV. The websocket 'finally'
            # normally finalizes it, but /end blocks the event loop, so it may not
            # have run yet — force it here (handles the /end-vs-websocket race).
            wav = self._ensure_finalized_wav(meeting_id)

            # Backward-compat: if transcript rows already exist (legacy real-time
            # transcription path), just diarize/relabel them — do not re-transcribe.
            existing = self.db.query(Transcript).filter(
                Transcript.meeting_id == meeting_id
            ).count()
            if existing > 0:
                logger.info(
                    f"Meeting {meeting_id} already has {existing} transcript rows; "
                    f"diarizing in place instead of re-transcribing."
                )
                try:
                    self._diarize_live(meeting_id)
                except Exception as e:
                    logger.error(f"Diarization skipped for meeting {meeting_id}: {e}")
                speakers_created = self._ensure_speakers_from_transcripts(meeting_id)
                self._generate_summary(meeting_id)
                self._cleanup_session(session_token, None)
                return {
                    "success": True,
                    "transcript_count": existing,
                    "speakers": max(speakers_created, 1),
                    "language": "en",
                    "text_length": 0,
                }

            if not wav:
                logger.warning(f"No live audio captured for meeting {meeting_id}")
                self._cleanup_session(session_token, None)
                return {
                    "success": False,
                    "error": "No audio captured",
                    "transcript_count": 0,
                    "speakers": 0,
                }

            # Record-only live meeting: transcribe the WHOLE recording ONCE and
            # always in English (translate=True) so the base transcript is English
            # and can be translated on demand from the meeting page.
            logger.info(f"Transcribing live recording (English) for meeting {meeting_id}: {wav}")
            segments = self.whisper_service.transcribe(wav, translate=True)
            segments = [s for s in (segments or []) if (s.get("text") or "").strip()]

            if not segments:
                logger.warning(f"Transcription produced no text for meeting {meeting_id}")
                self._cleanup_session(session_token, None)
                return {
                    "success": False,
                    "error": "Transcription failed",
                    "transcript_count": 0,
                    "speakers": 0,
                }

            # Persist one row per (English) segment, all Speaker 1 for now —
            # diarization relabels them below.
            transcripts_created = 0
            text_length = 0
            for seg in segments:
                text = (seg.get("text") or "").strip()
                self.db.add(Transcript(
                    meeting_id=meeting_id,
                    text=text,
                    speaker=seg.get("speaker", "Speaker 1"),
                    language=seg.get("language", "en"),
                    start_time=float(seg.get("start_time", 0.0) or 0.0),
                    end_time=float(seg.get("end_time", 0.0) or 0.0),
                    confidence=float(seg.get("confidence", 0.9) or 0.9),
                    is_final=True,
                ))
                transcripts_created += 1
                text_length += len(text)
            self.db.commit()
            logger.info(
                f"Saved {transcripts_created} English transcript segments for meeting {meeting_id}"
            )

            # Speaker diarization on the same WAV → relabel the rows in place.
            try:
                self._diarize_live(meeting_id)
            except Exception as e:
                logger.error(f"Diarization skipped for meeting {meeting_id}: {e}")

            speakers_created = self._ensure_speakers_from_transcripts(meeting_id)
            self._generate_summary(meeting_id)
            self._cleanup_session(session_token, None)

            logger.info(
                f"Audio processing complete for meeting {meeting_id}: "
                f"{transcripts_created} transcripts, {speakers_created} speakers"
            )
            return {
                "success": True,
                "transcript_count": transcripts_created,
                "speakers": max(speakers_created, 1),
                "language": "en",
                "text_length": text_length,
            }

        except Exception as e:
            logger.error(
                f"Error processing meeting audio: {str(e)}",
                exc_info=True
            )
            self.db.rollback()

            # Cleanup even on error
            try:
                self._cleanup_session(session_token, None)
            except:
                pass

            return {
                "success": False,
                "error": str(e),
                "transcript_count": 0,
                "speakers": 0
            }

    def _ensure_finalized_wav(self, meeting_id: int) -> Optional[str]:
        """Return the finalized live-recording WAV path, forcing finalization if
        the websocket handler hasn't wrapped the PCM yet (the /end request blocks
        the event loop, so its 'finally' can be delayed). Idempotent: whichever of
        /end or the websocket finalizes first wins; the other becomes a no-op."""
        import time
        from app.services.live_audio_recorder import live_audio_recorder

        meeting = self.db.query(Meeting).filter(Meeting.id == meeting_id).first()
        wav = meeting.audio_url if meeting else None
        if wav and os.path.exists(wav):
            return wav

        # Wrap the accumulated PCM into a WAV, retrying briefly in case the final
        # segment is still being appended.
        for _ in range(10):  # up to ~5s
            wav = live_audio_recorder.finalize(meeting_id)
            if wav:
                break
            time.sleep(0.5)

        if wav and meeting:
            meeting.audio_url = wav
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
        return wav

    def _generate_summary(self, meeting_id: int) -> None:
        """Generate and persist the meeting minutes now so they are ready the
        moment the meeting page loads (fails soft — the page can also regenerate
        on demand)."""
        try:
            from app.models.summary import Summary
            if self.db.query(Summary).filter(Summary.meeting_id == meeting_id).first():
                return
            rows = self.db.query(Transcript).filter(
                Transcript.meeting_id == meeting_id
            ).all()
            full_text = " ".join((r.text or "") for r in rows).strip()
            if not full_text:
                return
            data = self.summary_service.generate_summary(full_text)
            if data:
                self.db.add(Summary(
                    meeting_id=meeting_id,
                    summary_text=data.get("summary"),
                    key_points=data.get("key_points", []),
                    action_items=data.get("action_items", []),
                    sentiment=data.get("sentiment", "neutral"),
                ))
                self.db.commit()
                logger.info(f"Minutes generated for meeting {meeting_id}")
        except Exception as e:
            logger.error(f"Minutes generation failed for meeting {meeting_id}: {e}")
            self.db.rollback()

    def _diarize_live(self, meeting_id: int) -> None:
        """Diarize the persisted live WAV and relabel existing transcript rows in place."""
        meeting = self.db.query(Meeting).filter(Meeting.id == meeting_id).first()
        wav = meeting.audio_url if meeting else None
        if not wav or not os.path.exists(wav):
            logger.info(f"No persisted WAV for meeting {meeting_id}; skipping diarization")
            return

        from app.services.diarization_service import diarization_service
        turns = diarization_service.diarize(wav)
        if not turns:
            return

        rows = self.db.query(Transcript).filter(
            Transcript.meeting_id == meeting_id
        ).order_by(Transcript.start_time).all()
        segs = [
            {"start_time": r.start_time, "end_time": r.end_time,
             "text": r.text, "speaker": r.speaker}
            for r in rows
        ]
        labeled = diarization_service.align_speakers(segs, turns)
        for row, lab in zip(rows, labeled):
            row.speaker = lab["speaker"]
        self.db.commit()
        logger.info(
            f"Live diarization meeting {meeting_id}: "
            f"speakers={sorted({l['speaker'] for l in labeled})}"
        )

    def _ensure_speakers_from_transcripts(self, meeting_id: int) -> int:
        """Create Speaker rows for any speakers present in a meeting's
        transcripts but missing a Speaker record. Returns the number created.
        """
        try:
            transcripts = self.db.query(Transcript).filter(
                Transcript.meeting_id == meeting_id
            ).all()
            speaker_names = []
            for t in transcripts:
                name = t.speaker or "Speaker 1"
                if name not in speaker_names:
                    speaker_names.append(name)

            existing_names = {
                s.speaker_name
                for s in self.db.query(Speaker).filter(
                    Speaker.meeting_id == meeting_id
                ).all()
            }

            created = 0
            for idx, name in enumerate(speaker_names, start=1):
                if name in existing_names:
                    continue
                words = sum(
                    len((t.text or "").split())
                    for t in transcripts if (t.speaker or "Speaker 1") == name
                )
                self.db.add(Speaker(
                    meeting_id=meeting_id,
                    speaker_number=idx,
                    speaker_name=name,
                    talk_time_seconds=0,
                    word_count=words,
                ))
                created += 1

            if created:
                self.db.commit()
            return created
        except Exception as e:
            logger.warning(f"Could not ensure speaker rows for meeting {meeting_id}: {e}")
            self.db.rollback()
            return 0

    def _cleanup_session(
        self,
        session_token: str,
        audio_file_path: Optional[str]
    ) -> None:
        """
        Clean up session data and temporary files.
        
        Args:
            session_token: Session identifier
            audio_file_path: Path to audio file to delete (if any)
        """
        try:
            # Remove from memory
            if session_token in self.audio_chunks:
                chunk_count = len(self.audio_chunks[session_token])
                del self.audio_chunks[session_token]
                logger.debug(
                    f"Cleaned up {chunk_count} audio chunks from memory "
                    f"for session {session_token}"
                )
            
            # Remove temporary audio file
            if audio_file_path and os.path.exists(audio_file_path):
                os.remove(audio_file_path)
                logger.debug(f"Deleted temporary audio file: {audio_file_path}")

        except Exception as e:
            logger.warning(f"Error during cleanup: {str(e)}")
    
    def get_session_stats(self, session_token: str) -> dict:
        """
        Get statistics about a live session's audio data.
        
        Args:
            session_token: Session identifier
            
        Returns:
            dict: Statistics including chunk count and total bytes
        """
        chunks = self.audio_chunks.get(session_token, [])
        total_bytes = sum(len(chunk) for chunk in chunks)
        
        return {
            "chunk_count": len(chunks),
            "total_bytes": total_bytes,
            "avg_chunk_size": total_bytes // len(chunks) if chunks else 0
        }
