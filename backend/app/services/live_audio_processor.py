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
from app.services.speaker_diarization import SpeakerDiarizationService
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
        self.speaker_service = SpeakerDiarizationService()  # No db parameter
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
            
            # Step 1: Combine audio chunks
            audio_file_path = self._combine_audio_chunks(session_token)
            
            if not audio_file_path:
                logger.warning(
                    f"No audio to process for meeting {meeting_id}"
                )
                return {
                    "success": False,
                    "error": "No audio chunks found",
                    "transcript_count": 0,
                    "speakers": 0
                }
            
            # Step 2: Transcribe audio
            logger.info(f"Transcribing audio file: {audio_file_path}")
            transcription_result = self.whisper_service.transcribe(
                audio_file_path
            )
            
            # WhisperService.transcribe() returns a LIST of segments
            if not transcription_result or len(transcription_result) == 0:
                logger.warning(f"Transcription failed for meeting {meeting_id}")
                return {
                    "success": False,
                    "error": "Transcription failed",
                    "transcript_count": 0,
                    "speakers": 0
                }
            
            # Extract text from the first segment (or combine all segments)
            first_segment = transcription_result[0]
            full_text = first_segment.get("text", "")
            language = first_segment.get("language", "en")
            
            logger.info(
                f"Transcription result: {len(transcription_result)} segments, "
                f"first segment text length: {len(full_text)} characters"
            )
            
            logger.info(
                f"Transcription complete: {len(full_text)} characters, "
                f"language: {language}"
            )
            
            # Step 3: Apply speaker diarization
            logger.info(f"Applying speaker diarization")
            
            try:
                diarization_result = self.speaker_service.diarize_audio(
                    audio_file_path,
                    session_token
                )
                
                # Create speaker records
                speakers_created = 0
                for speaker_num, speaker_data in diarization_result.items():
                    speaker = Speaker(
                        meeting_id=meeting_id,
                        speaker_number=speaker_num,
                        speaker_name=f"Speaker {speaker_num}",
                        talk_time_seconds=speaker_data.get("talk_time", 0),
                        word_count=0  # Will be calculated from transcripts
                    )
                    self.db.add(speaker)
                    speakers_created += 1
                
                logger.info(f"Created {speakers_created} speaker records")
                
            except Exception as e:
                logger.warning(
                    f"Speaker diarization failed: {str(e)}, "
                    f"using single speaker"
                )
                # Fallback: create single speaker
                speaker = Speaker(
                    meeting_id=meeting_id,
                    speaker_number=1,
                    speaker_name="Speaker 1",
                    talk_time_seconds=0,
                    word_count=len(full_text.split())
                )
                self.db.add(speaker)
                speakers_created = 1
            
            # Step 4: Create transcript record
            transcript = Transcript(
                meeting_id=meeting_id,
                text=full_text,
                speaker=first_segment.get("speaker", "Speaker 1"),
                language=language,
                start_time=first_segment.get("start_time", 0),
                end_time=first_segment.get("end_time", 0),
                confidence=first_segment.get("confidence", 0.0),
                is_final=True
            )
            self.db.add(transcript)
            
            # Step 5: Generate summary
            logger.info(f"Generating meeting summary")
            
            try:
                summary_result = self.summary_service.generate_summary(full_text)
                
                # Update meeting with summary
                meeting = self.db.query(Meeting).filter(
                    Meeting.id == meeting_id
                ).first()
                
                if meeting and summary_result:
                    # Summary service returns a Summary object, commit it
                    self.db.commit()
                    logger.info(f"Summary generated successfully")
                
            except Exception as e:
                logger.error(f"Summary generation failed: {str(e)}")
                # Continue even if summary fails
            
            # Commit all changes
            self.db.commit()
            
            # Step 6: Cleanup
            self._cleanup_session(session_token, audio_file_path)
            
            logger.info(
                f"Audio processing complete for meeting {meeting_id}: "
                f"1 transcript, {speakers_created} speakers"
            )
            
            return {
                "success": True,
                "transcript_count": 1,
                "speakers": speakers_created,
                "language": language,
                "text_length": len(full_text)
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
            
            # Clean up speaker diarization session
            try:
                self.speaker_service.cleanup_session(session_token)
            except:
                pass
                
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
