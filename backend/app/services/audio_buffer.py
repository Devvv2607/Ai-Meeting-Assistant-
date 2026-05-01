"""Audio buffering service for live meeting audio streaming.

This module handles buffering of audio chunks received from the frontend
and assembles them into segments suitable for transcription.
"""

import io
import logging
from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class AudioSegment:
    """Represents a complete audio segment ready for transcription"""
    data: bytes
    duration: float
    timestamp: datetime
    sequence_start: int
    sequence_end: int


class AudioBuffer:
    """Buffer audio chunks into segments for transcription.
    
    The AudioBuffer receives 100ms audio chunks from the frontend and
    buffers them into 1-second segments suitable for Whisper transcription.
    It handles audio format conversion from WebM/Opus to WAV format.
    
    Attributes:
        segment_duration: Target duration for segments in seconds (default: 1.0)
        sample_rate: Audio sample rate in Hz (default: 16000 for Whisper)
        buffer: List of buffered audio chunks
        buffer_duration: Current duration of buffered audio in seconds
        total_segments: Total number of segments created
    """
    
    def __init__(self, segment_duration: float = 1.0, sample_rate: int = 16000):
        """Initialize AudioBuffer.
        
        Args:
            segment_duration: Target duration for segments in seconds
            sample_rate: Audio sample rate in Hz (Whisper requires 16kHz)
        """
        self.segment_duration = segment_duration
        self.sample_rate = sample_rate
        self.buffer: List[bytes] = []
        self.buffer_duration: float = 0.0
        self.total_segments: int = 0
        self.chunk_metadata: List[dict] = []
        
        logger.info(
            f"AudioBuffer initialized: segment_duration={segment_duration}s, "
            f"sample_rate={sample_rate}Hz"
        )
    
    def add_chunk(
        self,
        chunk: bytes,
        duration: float,
        metadata: Optional[dict] = None
    ) -> Optional[AudioSegment]:
        """Add audio chunk to buffer and return segment if ready.
        
        This method buffers incoming audio chunks until the accumulated
        duration reaches the target segment duration. When a segment is
        ready, it returns the combined audio data.
        
        Args:
            chunk: Raw audio data bytes (WebM/Opus format from frontend)
            duration: Duration of the chunk in seconds
            metadata: Optional metadata (timestamp, sequence_number, etc.)
        
        Returns:
            AudioSegment if a complete segment is ready, None otherwise
        """
        if not chunk:
            logger.warning("Received empty audio chunk, skipping")
            return None
        
        # Add chunk to buffer
        self.buffer.append(chunk)
        self.buffer_duration += duration
        
        # Store metadata for tracking
        if metadata:
            self.chunk_metadata.append(metadata)
        
        logger.debug(
            f"Added chunk: {len(chunk)} bytes, {duration:.3f}s "
            f"(buffer: {self.buffer_duration:.3f}s)"
        )
        
        # Check if we have enough audio for a segment
        # Use small epsilon to handle floating point precision issues
        EPSILON = 0.001  # 1ms tolerance
        if self.buffer_duration >= (self.segment_duration - EPSILON):
            return self._create_segment()
        
        return None
    
    def flush(self) -> Optional[AudioSegment]:
        """Flush remaining audio in buffer as a segment.
        
        This method should be called when the audio stream ends to
        process any remaining buffered audio that hasn't reached the
        target segment duration.
        
        Returns:
            AudioSegment with remaining audio, or None if buffer is empty
        """
        if not self.buffer:
            logger.debug("Buffer is empty, nothing to flush")
            return None
        
        logger.info(
            f"Flushing buffer: {len(self.buffer)} chunks, "
            f"{self.buffer_duration:.3f}s"
        )
        
        return self._create_segment()
    
    def _create_segment(self) -> Optional[AudioSegment]:
        """Create an audio segment from buffered chunks.
        
        This internal method combines buffered chunks, converts the format
        if necessary, and creates an AudioSegment object.
        
        Returns:
            AudioSegment with combined audio data
        """
        if not self.buffer:
            return None
        
        try:
            # Combine all buffered chunks
            combined_audio = b''.join(self.buffer)
            
            # Convert from WebM/Opus to WAV format for Whisper
            # If conversion fails, use original data as fallback
            wav_audio = self._convert_to_wav(combined_audio)
            if wav_audio is None:
                logger.warning("Audio conversion failed, using original data")
                wav_audio = combined_audio
            
            # Get sequence range from metadata
            sequence_start = (
                self.chunk_metadata[0].get('sequence_number', 0)
                if self.chunk_metadata else 0
            )
            sequence_end = (
                self.chunk_metadata[-1].get('sequence_number', 0)
                if self.chunk_metadata else 0
            )
            
            # Create segment
            segment = AudioSegment(
                data=wav_audio,
                duration=self.buffer_duration,
                timestamp=datetime.utcnow(),
                sequence_start=sequence_start,
                sequence_end=sequence_end
            )
            
            self.total_segments += 1
            
            logger.info(
                f"Created segment #{self.total_segments}: "
                f"{len(wav_audio)} bytes, {self.buffer_duration:.3f}s, "
                f"seq {sequence_start}-{sequence_end}"
            )
            
            # Clear buffer
            self.buffer.clear()
            self.buffer_duration = 0.0
            self.chunk_metadata.clear()
            
            return segment
            
        except Exception as e:
            logger.error(f"Error creating audio segment: {e}", exc_info=True)
            # Clear buffer on error to prevent corruption
            self.buffer.clear()
            self.buffer_duration = 0.0
            self.chunk_metadata.clear()
            return None
    
    def _convert_to_wav(self, audio_data: bytes) -> Optional[bytes]:
        """Convert audio from WebM/Opus to WAV format.
        
        Whisper requires WAV format audio at 16kHz sample rate.
        This method uses pydub to handle the conversion.
        
        Args:
            audio_data: Raw audio bytes in WebM/Opus format
        
        Returns:
            Audio bytes in WAV format at 16kHz, or None if conversion fails
        """
        try:
            from pydub import AudioSegment as PydubSegment
            
            # Load audio from bytes
            # Try WebM first, then fall back to other formats
            audio = None
            for format_name in ['webm', 'ogg', 'opus']:
                try:
                    audio = PydubSegment.from_file(
                        io.BytesIO(audio_data),
                        format=format_name
                    )
                    logger.debug(f"Successfully loaded audio as {format_name}")
                    break
                except Exception as format_error:
                    logger.debug(f"Failed to load as {format_name}: {format_error}")
                    continue
            
            if audio is None:
                logger.warning(
                    "Could not detect audio format, attempting raw conversion"
                )
                # Last resort: try without specifying format
                audio = PydubSegment.from_file(io.BytesIO(audio_data))
            
            # Convert to mono if stereo
            if audio.channels > 1:
                audio = audio.set_channels(1)
                logger.debug("Converted stereo to mono")
            
            # Resample to 16kHz (Whisper requirement)
            if audio.frame_rate != self.sample_rate:
                audio = audio.set_frame_rate(self.sample_rate)
                logger.debug(f"Resampled from {audio.frame_rate}Hz to {self.sample_rate}Hz")
            
            # Export as WAV
            wav_buffer = io.BytesIO()
            audio.export(
                wav_buffer,
                format='wav',
                parameters=['-ar', str(self.sample_rate), '-ac', '1']
            )
            wav_data = wav_buffer.getvalue()
            
            logger.debug(
                f"Converted audio: {len(audio_data)} bytes -> {len(wav_data)} bytes WAV"
            )
            
            return wav_data
            
        except ImportError:
            logger.warning(
                "pydub not available - cannot convert audio format. "
                "Install with: pip install pydub"
            )
            # Return None to signal conversion failure
            return None
            
        except Exception as e:
            logger.debug(f"Audio format conversion failed: {e}")
            # Return None to signal conversion failure
            return None
    
    def get_stats(self) -> dict:
        """Get buffer statistics.
        
        Returns:
            Dictionary with buffer statistics
        """
        return {
            'total_segments': self.total_segments,
            'buffer_chunks': len(self.buffer),
            'buffer_duration': self.buffer_duration,
            'segment_duration': self.segment_duration,
            'sample_rate': self.sample_rate
        }
    
    def reset(self):
        """Reset buffer state.
        
        Clears all buffered data and resets counters.
        Useful for starting a new session or recovering from errors.
        """
        self.buffer.clear()
        self.buffer_duration = 0.0
        self.chunk_metadata.clear()
        self.total_segments = 0
        logger.info("AudioBuffer reset")
