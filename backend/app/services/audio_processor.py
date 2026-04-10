from typing import Dict, List, Optional
import logging
from app.utils.audio_utils import AudioProcessor
from app.services.whisper_service import whisper_service
from app.services.embedding_service import embedding_service
from pyannote.audio import Pipeline
import torch

logger = logging.getLogger(__name__)


class AudioProcessingService:
    """Service for orchestrating audio processing pipeline"""

    def __init__(self):
        """Initialize audio processing service"""
        self.audio_processor = AudioProcessor()
        try:
            # Load pyannote speaker diarization model
            # Note: Requires authentication token
            self.diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.0",
                use_auth_token=False,  # Set to your token if available
            )
        except Exception as e:
            logger.warning(f"Speaker diarization model not available: {e}")
            self.diarization_pipeline = None

    def process_meeting(
        self,
        audio_path: str,
        meeting_id: int,
    ) -> Optional[Dict]:
        """Process meeting audio file

        Args:
            audio_path: Path to audio file
            meeting_id: ID of the meeting

        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"Starting audio processing for meeting {meeting_id}")

            # Step 1: Get audio duration
            duration = self.audio_processor.get_duration(audio_path)
            if not duration:
                logger.error(f"Could not determine audio duration for {audio_path}")
                return None

            logger.info(f"Audio duration: {duration} seconds")

            # Step 2: Split audio into chunks
            chunks = self.audio_processor.split_audio(audio_path, chunk_duration=300)
            if not chunks:
                logger.error(f"Could not split audio file")
                return None

            logger.info(f"Split audio into {len(chunks)} chunks")

            # Step 3: Transcribe chunks
            transcripts = []
            for chunk_path in chunks:
                result = whisper_service.transcribe(chunk_path)
                transcripts.extend(result)

            logger.info(f"Transcribed {len(transcripts)} segments")

            # Step 4: Perform speaker diarization
            if self.diarization_pipeline:
                diarization = self._perform_diarization(audio_path)
                transcripts = self._merge_diarization(transcripts, diarization)
            else:
                logger.warning("Speaker diarization not available, using default labels")

            # Step 5: Generate embeddings
            embedding_results = self._generate_segment_embeddings(transcripts)

            return {
                "meeting_id": meeting_id,
                "duration": duration,
                "transcripts": transcripts,
                "embeddings": embedding_results,
                "total_segments": len(transcripts),
            }

        except Exception as e:
            logger.error(f"Error processing meeting: {e}")
            return None

    def _perform_diarization(self, audio_path: str) -> Optional[Dict]:
        """Perform speaker diarization

        Args:
            audio_path: Path to audio file

        Returns:
            Diarization results
        """
        try:
            if self.diarization_pipeline is None:
                return None

            diarization = self.diarization_pipeline(audio_path)
            return diarization
        except Exception as e:
            logger.error(f"Error performing diarization: {e}")
            return None

    def _merge_diarization(
        self, transcripts: List[Dict], diarization: Optional[Dict]
    ) -> List[Dict]:
        """Merge diarization results with transcripts

        Args:
            transcripts: List of transcript segments
            diarization: Diarization results

        Returns:
            Updated transcripts with speaker labels
        """
        if diarization is None:
            return transcripts

        try:
            for transcript in transcripts:
                # Find speaker for this segment based on timing
                speaker = "Unknown"
                # This is a simplified version - full implementation would
                # properly match diarization segments with transcript segments
                transcript["speaker"] = speaker

            return transcripts
        except Exception as e:
            logger.error(f"Error merging diarization: {e}")
            return transcripts

    def _generate_segment_embeddings(self, transcripts: List[Dict]) -> List[List[float]]:
        """Generate embeddings for transcript segments

        Args:
            transcripts: List of transcript segments

        Returns:
            List of embeddings
        """
        try:
            texts = [t["text"] for t in transcripts]
            embeddings = embedding_service.encode(texts)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return []


# Global audio processing service instance
audio_processing_service = AudioProcessingService()
