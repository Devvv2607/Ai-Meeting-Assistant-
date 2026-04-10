from typing import List, Dict, Optional
import json
import logging
from faster_whisper import WhisperModel
from app.config import settings

logger = logging.getLogger(__name__)


class WhisperService:
    """Service for speech-to-text transcription using Whisper"""

    def __init__(self, model_size: str = settings.WHISPER_MODEL):
        """Initialize Whisper model

        Args:
            model_size: Model size (tiny, base, small, medium, large)
        """
        try:
            device = "cuda" if settings.DEVICE == "cuda" else "cpu"
            self.model = WhisperModel(model_size, device=device, compute_type="float32")
            logger.info(f"Loaded Whisper model: {model_size} on {device}")
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
            raise

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> List[Dict]:
        """Transcribe audio file

        Args:
            audio_path: Path to audio file
            language: Optional language code (e.g., 'en', 'es')

        Returns:
            List of transcribed segments with timing
        """
        try:
            segments, info = self.model.transcribe(
                audio_path,
                language=language,
                beam_size=5,
                best_of=5,
                temperature=0.0,
            )

            results = []
            for segment in segments:
                results.append(
                    {
                        "speaker": "Speaker 1",  # Basic speaker label
                        "text": segment.text.strip(),
                        "start": segment.start,
                        "end": segment.end,
                        "confidence": segment.confidence,
                    }
                )

            logger.info(
                f"Successfully transcribed {audio_path}. Found {len(results)} segments"
            )
            return results

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return []

    def transcribe_batch(
        self,
        audio_paths: List[str],
        language: Optional[str] = None,
    ) -> Dict[str, List[Dict]]:
        """Transcribe multiple audio files

        Args:
            audio_paths: List of paths to audio files
            language: Optional language code

        Returns:
            Dictionary mapping audio paths to transcription results
        """
        results = {}
        for audio_path in audio_paths:
            results[audio_path] = self.transcribe(audio_path, language)
        return results


# Global Whisper service instance
whisper_service = WhisperService()
