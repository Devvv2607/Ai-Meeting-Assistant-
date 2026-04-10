import librosa
import numpy as np
from typing import List, Tuple, Optional
import soundfile as sf
import logging

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Service for audio processing"""

    @staticmethod
    def get_duration(file_path: str) -> Optional[float]:
        """Get audio duration in seconds"""
        try:
            y, sr = librosa.load(file_path, sr=None)
            duration = librosa.get_duration(y=y, sr=sr)
            return duration
        except Exception as e:
            logger.error(f"Error getting audio duration: {e}")
            return None

    @staticmethod
    def split_audio(
        file_path: str, chunk_duration: int = 300, output_dir: str = "/tmp"
    ) -> List[str]:
        """Split audio into chunks of specified duration

        Args:
            file_path: Path to audio file
            chunk_duration: Duration of each chunk in seconds
            output_dir: Directory to save chunks

        Returns:
            List of paths to audio chunks
        """
        try:
            y, sr = librosa.load(file_path, sr=None)
            chunk_samples = chunk_duration * sr

            chunks = []
            for i in range(0, len(y), chunk_samples):
                chunk = y[i : i + chunk_samples]
                chunk_path = f"{output_dir}/chunk_{i // chunk_samples}.wav"
                sf.write(chunk_path, chunk, sr)
                chunks.append(chunk_path)

            logger.info(f"Split audio into {len(chunks)} chunks")
            return chunks
        except Exception as e:
            logger.error(f"Error splitting audio: {e}")
            return []

    @staticmethod
    def merge_audio(chunk_paths: List[str], output_path: str) -> bool:
        """Merge audio chunks into single file

        Args:
            chunk_paths: List of paths to audio chunks
            output_path: Path to save merged audio

        Returns:
            True if successful, False otherwise
        """
        try:
            audio_data = []
            sr = None

            for chunk_path in chunk_paths:
                y, sr = librosa.load(chunk_path, sr=sr)
                audio_data.append(y)

            merged = np.concatenate(audio_data)
            sf.write(output_path, merged, sr)

            logger.info(f"Merged audio saved to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error merging audio: {e}")
            return False

    @staticmethod
    def convert_format(
        input_path: str, output_path: str, target_sr: int = 16000
    ) -> bool:
        """Convert audio to target format and sample rate

        Args:
            input_path: Path to input audio file
            output_path: Path to save converted audio
            target_sr: Target sample rate

        Returns:
            True if successful, False otherwise
        """
        try:
            y, sr = librosa.load(input_path, sr=target_sr)
            sf.write(output_path, y, target_sr)
            logger.info(f"Converted audio saved to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error converting audio: {e}")
            return False
