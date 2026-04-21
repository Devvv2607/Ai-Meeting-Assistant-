# Temporary stub to avoid ML dependencies
# import librosa
# import numpy as np
# import soundfile as sf
from typing import List, Optional
import logging
import os

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Service for audio processing (stub version without ML dependencies)"""

    @staticmethod
    def get_duration(file_path: str) -> Optional[float]:
        """Get audio duration in seconds (stub - estimates from file size)"""
        try:
            # Rough estimate: 1MB ≈ 60 seconds for typical audio
            file_size = os.path.getsize(file_path)
            estimated_duration = (file_size / 1024 / 1024) * 60
            logger.info(f"Estimated audio duration: {estimated_duration:.2f}s (file size: {file_size} bytes)")
            return estimated_duration
        except Exception as e:
            logger.error(f"Error getting audio duration: {e}")
            return None

    @staticmethod
    def split_audio(
        file_path: str, chunk_duration: int = 300, output_dir: str = "/tmp"
    ) -> List[str]:
        """Split audio into chunks (stub - not implemented)

        Args:
            file_path: Path to audio file
            chunk_duration: Duration of each chunk in seconds
            output_dir: Directory to save chunks

        Returns:
            Empty list (stub implementation)
        """
        logger.warning("Audio splitting not available without librosa")
        return []

    @staticmethod
    def merge_audio(chunk_paths: List[str], output_path: str) -> bool:
        """Merge audio chunks (stub - not implemented)

        Args:
            chunk_paths: List of paths to audio chunks
            output_path: Path to save merged audio

        Returns:
            False (stub implementation)
        """
        logger.warning("Audio merging not available without librosa")
        return False

    @staticmethod
    def convert_format(
        input_path: str, output_path: str, target_sr: int = 16000
    ) -> bool:
        """Convert audio format (stub - not implemented)

        Args:
            input_path: Path to input audio file
            output_path: Path to save converted audio
            target_sr: Target sample rate

        Returns:
            False (stub implementation)
        """
        logger.warning("Audio conversion not available without librosa")
        return False
