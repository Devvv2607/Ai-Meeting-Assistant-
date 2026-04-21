from typing import Dict, List, Optional
import logging
from app.utils.audio_utils import AudioProcessor
from app.services.whisper_service import whisper_service
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


class AudioProcessingService:
    """Service for orchestrating audio processing pipeline"""

    def __init__(self):
        """Initialize audio processing service"""
        self.audio_processor = AudioProcessor()
        self.diarization_pipeline = None
        logger.info("Audio processing service initialized")

    def process_meeting(
        self,
        audio_path: str,
        meeting_id: int,
    ) -> Optional[Dict]:
        """Process meeting audio file with real transcription

        Args:
            audio_path: Path to audio file
            meeting_id: ID of the meeting

        Returns:
            Dictionary with processing results including transcripts
        """
        try:
            logger.info(f"Processing meeting {meeting_id} with real transcription")

            # Get audio duration
            duration = self.audio_processor.get_duration(audio_path)

            # Transcribe audio using Gemini
            transcripts = whisper_service.transcribe(audio_path)
            
            if not transcripts:
                logger.warning(f"No transcripts generated for meeting {meeting_id}")
                return {
                    "meeting_id": meeting_id,
                    "duration": duration or 0,
                    "transcripts": [],
                    "embeddings": [],
                    "total_segments": 0,
                }

            logger.info(f"Generated {len(transcripts)} transcript segments for meeting {meeting_id}")

            # Generate embeddings (stub for now)
            embeddings = self._generate_segment_embeddings(transcripts)

            return {
                "meeting_id": meeting_id,
                "duration": duration or 0,
                "transcripts": transcripts,
                "embeddings": embeddings,
                "total_segments": len(transcripts),
            }

        except Exception as e:
            logger.error(f"Error processing meeting: {e}")
            return None

    def _perform_diarization(self, audio_path: str) -> Optional[Dict]:
        """Perform speaker diarization (not implemented yet)"""
        logger.warning("Speaker diarization not available yet")
        return None

    def _merge_diarization(
        self, transcripts: List[Dict], diarization: Optional[Dict]
    ) -> List[Dict]:
        """Merge diarization results (returns unchanged transcripts)"""
        return transcripts

    def _generate_segment_embeddings(self, transcripts: List[Dict]) -> List[List[float]]:
        """Generate embeddings (stub - returns empty list)"""
        logger.warning("Embedding generation not available yet")
        return []


# Global audio processing service instance
audio_processing_service = AudioProcessingService()
