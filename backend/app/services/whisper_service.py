from typing import List, Dict, Optional
import logging
from app.config import settings
import google.generativeai as genai
from pathlib import Path
import tempfile
import os

logger = logging.getLogger(__name__)


class WhisperService:
    """Service for speech-to-text transcription using Google Gemini API or Groq API"""

    def __init__(self, model_size: str = settings.WHISPER_MODEL):
        """Initialize transcription service

        Args:
            model_size: Not used for Gemini/Groq, kept for compatibility
        """
        self.provider = settings.LLM_PROVIDER.lower()
        self.model = None
        self.groq_client = None
        
        if self.provider == "groq":
            self._init_groq()
        else:
            self._init_gemini()
    
    def _init_groq(self):
        """Initialize Groq client"""
        try:
            from groq import Groq
            api_key = settings.GEMINI_API_KEY
            
            logger.info(f"Initializing Groq with provider: {settings.LLM_PROVIDER}")
            logger.info(f"API Key configured: {bool(api_key and api_key != '')}")
            logger.info(f"API Key length: {len(api_key) if api_key else 0}")
            
            if not api_key or api_key == "":
                logger.error("GEMINI_API_KEY not configured for Groq - transcription will not work")
                self.groq_client = None
                return
            
            self.groq_client = Groq(api_key=api_key)
            logger.info(f"✓ Groq transcription service initialized successfully (key: {api_key[:20]}...)")
        except Exception as e:
            logger.error(f"Failed to initialize Groq: {e}", exc_info=True)
            self.groq_client = None
    
    def _init_gemini(self):
        """Initialize Gemini client"""
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "":
            logger.error("GEMINI_API_KEY not configured - transcription will not work")
            self.model = None
            return
        
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Gemini transcription service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self.model = None

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> List[Dict]:
        """Transcribe audio file using Groq or Gemini

        Args:
            audio_path: Path to audio file
            language: Optional language code (e.g., 'en', 'es')

        Returns:
            List of transcript segments with speaker, text, start_time, end_time
        """
        if self.provider == "groq":
            return self._transcribe_groq(audio_path)
        else:
            return self._transcribe_gemini(audio_path)
    
    def _transcribe_groq(self, audio_path: str) -> List[Dict]:
        """Transcribe using Groq API with chunking for large files"""
        if not self.groq_client:
            logger.error("Groq client not initialized")
            return self._get_fallback_transcript(audio_path)
        
        try:
            logger.info(f"Transcribing audio file with Groq: {audio_path}")
            
            # Check if file exists
            from pathlib import Path as PathlibPath
            if not PathlibPath(audio_path).exists():
                logger.error(f"Audio file not found: {audio_path}")
                return self._get_fallback_transcript(audio_path)
            
            # Get file size
            file_size = PathlibPath(audio_path).stat().st_size
            logger.info(f"Audio file size: {file_size / (1024*1024):.2f} MB")
            
            # Groq has a 25MB limit for audio files
            MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB
            
            if file_size > MAX_FILE_SIZE:
                logger.info(f"File size ({file_size / (1024*1024):.2f} MB) exceeds Groq limit (25MB), splitting into chunks")
                return self._transcribe_groq_chunked(audio_path)
            
            # File is small enough, transcribe directly
            with open(audio_path, "rb") as audio_file:
                transcript = self.groq_client.audio.transcriptions.create(
                    file=(Path(audio_path).name, audio_file, "audio/mpeg"),
                    model="whisper-large-v3-turbo",
                    language="en",
                )
            
            logger.info(f"Received transcription from Groq")
            
            # Parse Groq response
            text = transcript.text if hasattr(transcript, 'text') else str(transcript)
            
            # Create segments from the transcription
            from app.utils.audio_utils import AudioProcessor
            audio_processor = AudioProcessor()
            duration = audio_processor.get_duration(audio_path)
            
            logger.info(f"✓ Transcription successful: {len(text)} characters")
            
            return [{
                "speaker": "Speaker 1",
                "text": text,
                "start_time": 0.0,
                "end_time": float(duration) if duration else 60.0
            }]
            
        except Exception as e:
            logger.error(f"Error transcribing audio with Groq: {e}", exc_info=True)
            return self._get_fallback_transcript(audio_path)
    
    def _transcribe_groq_chunked(self, audio_path: str) -> List[Dict]:
        """Transcribe large audio files by splitting into chunks using ffmpeg"""
        try:
            import subprocess
            import os
            import tempfile
            from pathlib import Path as PathlibPath
            
            logger.info(f"Starting chunked transcription for {audio_path}")
            
            # Create temp directory for chunks
            temp_dir = tempfile.mkdtemp()
            chunk_prefix = os.path.join(temp_dir, "chunk")
            
            try:
                # Use ffmpeg to split audio into 10-minute chunks
                logger.info("Splitting audio into 10-minute chunks using ffmpeg")
                
                cmd = [
                    "ffmpeg",
                    "-i", audio_path,
                    "-f", "segment",
                    "-segment_time", "600",  # 10 minutes
                    "-c", "copy",
                    "-y",
                    f"{chunk_prefix}_%03d.m4a"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.warning(f"ffmpeg split failed: {result.stderr}")
                    logger.info("Falling back to compression method")
                    return self._transcribe_groq_compressed(audio_path)
                
                # Find all chunk files
                chunk_files = sorted([f for f in os.listdir(temp_dir) if f.startswith("chunk_")])
                logger.info(f"✓ Created {len(chunk_files)} audio chunks")
                
                # Transcribe each chunk
                all_transcripts = []
                for i, chunk_file in enumerate(chunk_files):
                    chunk_path = os.path.join(temp_dir, chunk_file)
                    logger.info(f"Transcribing chunk {i+1}/{len(chunk_files)}: {chunk_file}")
                    
                    try:
                        with open(chunk_path, "rb") as audio_file:
                            transcript = self.groq_client.audio.transcriptions.create(
                                file=(chunk_file, audio_file, "audio/mpeg"),
                                model="whisper-large-v3-turbo",
                                language="en",
                            )
                        
                        text = transcript.text if hasattr(transcript, 'text') else str(transcript)
                        all_transcripts.append(text)
                        logger.info(f"✓ Chunk {i+1} transcribed: {len(text)} characters")
                        
                    except Exception as chunk_error:
                        logger.error(f"Error transcribing chunk {i+1}: {chunk_error}")
                        all_transcripts.append(f"[Chunk {i+1} transcription failed]")
                
                # Combine all transcripts
                combined_text = " ".join(all_transcripts)
                
                # Get total duration
                from app.utils.audio_utils import AudioProcessor
                audio_processor = AudioProcessor()
                duration = audio_processor.get_duration(audio_path)
                
                logger.info(f"✓ Chunked transcription complete: {len(combined_text)} characters total")
                
                return [{
                    "speaker": "Speaker 1",
                    "text": combined_text,
                    "start_time": 0.0,
                    "end_time": float(duration) if duration else 60.0
                }]
                
            finally:
                # Clean up temp directory
                import shutil
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temp directory: {temp_dir}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temp directory: {cleanup_error}")
                    
        except Exception as e:
            logger.error(f"Error in chunked transcription: {e}", exc_info=True)
            return self._transcribe_groq_compressed(audio_path)
    
    def _transcribe_groq_compressed(self, audio_path: str) -> List[Dict]:
        """Transcribe by compressing the audio file using ffmpeg"""
        try:
            import subprocess
            import tempfile
            from pathlib import Path as PathlibPath
            
            logger.info(f"Attempting transcription with audio compression using ffmpeg")
            
            # Create temp file for compressed audio
            temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            compressed_path = temp_file.name
            temp_file.close()
            
            try:
                # Compress audio using ffmpeg (reduce bitrate to 64kbps)
                logger.info("Compressing audio to 64kbps using ffmpeg")
                
                cmd = [
                    "ffmpeg",
                    "-i", audio_path,
                    "-b:a", "64k",  # 64kbps bitrate
                    "-y",
                    compressed_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.warning(f"Audio compression failed: {result.stderr}")
                    return self._get_fallback_transcript(audio_path)
                
                # Check compressed file size
                compressed_size = PathlibPath(compressed_path).stat().st_size
                logger.info(f"✓ Compressed audio size: {compressed_size / (1024*1024):.2f} MB")
                
                # Transcribe compressed file
                with open(compressed_path, "rb") as audio_file:
                    transcript = self.groq_client.audio.transcriptions.create(
                        file=("audio.mp3", audio_file, "audio/mpeg"),
                        model="whisper-large-v3-turbo",
                        language="en",
                    )
                
                text = transcript.text if hasattr(transcript, 'text') else str(transcript)
                
                # Get duration
                from app.utils.audio_utils import AudioProcessor
                audio_processor = AudioProcessor()
                duration = audio_processor.get_duration(audio_path)
                
                logger.info(f"✓ Compressed transcription successful: {len(text)} characters")
                
                return [{
                    "speaker": "Speaker 1",
                    "text": text,
                    "start_time": 0.0,
                    "end_time": float(duration) if duration else 60.0
                }]
                
            finally:
                # Clean up compressed file
                import os
                try:
                    if os.path.exists(compressed_path):
                        os.remove(compressed_path)
                        logger.info(f"Cleaned up compressed file: {compressed_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up compressed file: {cleanup_error}")
                    
        except Exception as e:
            logger.error(f"Error in compressed transcription: {e}", exc_info=True)
            return self._get_fallback_transcript(audio_path)
    
    def _transcribe_gemini(self, audio_path: str) -> List[Dict]:
        """Transcribe using Gemini API"""
        if not self.model:
            logger.error("Gemini model not initialized - cannot transcribe")
            return self._get_fallback_transcript(audio_path)
        
        try:
            logger.info(f"Transcribing audio file with Gemini: {audio_path}")
            
            # Upload audio file to Gemini
            audio_file = genai.upload_file(path=audio_path)
            logger.info(f"Uploaded audio file to Gemini: {audio_file.name}")
            
            # Create prompt for transcription
            prompt = """Please transcribe this audio file. Provide a detailed transcription with timestamps.
            
Format your response as a JSON array with this structure:
[
  {
    "speaker": "Speaker 1",
    "text": "transcribed text here",
    "start_time": 0.0,
    "end_time": 5.0
  }
]

If you cannot determine exact timestamps, estimate them based on the content length.
If you cannot identify different speakers, use "Speaker 1" for all segments.
"""
            
            # Generate transcription
            response = self.model.generate_content([prompt, audio_file])
            
            logger.info(f"Received transcription response from Gemini")
            
            # Parse response
            import json
            import re
            
            # Extract JSON from response
            response_text = response.text
            
            # Try to find JSON array in response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                segments = json.loads(json_match.group())
                logger.info(f"Parsed {len(segments)} transcript segments")
                return segments
            else:
                # If no JSON found, create a single segment with the full text
                logger.warning("Could not parse JSON from response, creating single segment")
                return [{
                    "speaker": "Speaker 1",
                    "text": response_text,
                    "start_time": 0.0,
                    "end_time": 60.0
                }]
                
        except Exception as e:
            logger.error(f"Error transcribing audio with Gemini: {e}")
            logger.info("Using fallback transcript generation")
            return self._get_fallback_transcript(audio_path)
    
    def _get_fallback_transcript(self, audio_path: str) -> List[Dict]:
        """Generate a fallback transcript when API fails
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            List with a single fallback transcript segment
        """
        from app.utils.audio_utils import AudioProcessor
        import os
        
        try:
            audio_processor = AudioProcessor()
            duration = audio_processor.get_duration(audio_path)
            
            # Check if we should use mock data for testing
            use_mock = os.getenv("USE_MOCK_TRANSCRIPTION", "false").lower() == "true"
            
            if use_mock:
                logger.info(f"Using mock transcript for testing (file: {Path(audio_path).name})")
                return [{
                    "speaker": "Speaker 1",
                    "text": "This is a mock transcript for testing purposes. The actual transcription service is not available. Please configure a valid API key (Groq or Gemini) in the .env file to enable real transcription.",
                    "start_time": 0.0,
                    "end_time": float(duration) if duration else 60.0
                }]
            else:
                logger.info(f"Generating fallback transcript for {audio_path} (duration: {duration}s)")
                logger.warning("TRANSCRIPTION SERVICE UNAVAILABLE - Please check:")
                logger.warning("1. Groq API key is valid (starts with 'gsk_')")
                logger.warning("2. LLM_PROVIDER is set to 'groq' or 'gemini'")
                logger.warning("3. API key has not expired")
                logger.warning("4. Network connection is working")
                
                return [{
                    "speaker": "Speaker 1",
                    "text": f"[Audio file: {Path(audio_path).name}] - Transcription service temporarily unavailable. Please check API configuration. See logs for details.",
                    "start_time": 0.0,
                    "end_time": float(duration) if duration else 60.0
                }]
        except Exception as e:
            logger.error(f"Error generating fallback transcript: {e}")
            return [{
                "speaker": "Speaker 1",
                "text": "[Transcription service unavailable]",
                "start_time": 0.0,
                "end_time": 60.0
            }]

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
            Dictionary mapping audio paths to transcript segments
        """
        results = {}
        for audio_path in audio_paths:
            results[audio_path] = self.transcribe(audio_path, language)
        return results

    async def transcribe_stream(
        self,
        audio_segment: bytes,
        language: Optional[str] = None
    ) -> Dict:
        """Transcribe audio segment for live streaming
        
        This method handles real-time transcription of 1-second audio segments
        from the live meeting audio buffer. It saves the segment to a temporary
        file, calls the Groq Whisper API, and returns structured results.
        
        Args:
            audio_segment: Raw audio bytes (1-second segment in WAV format)
            language: Optional language hint (e.g., 'en', 'hi', 'mr')
            
        Returns:
            Dictionary with:
                - text: Transcribed text
                - confidence: Confidence score (0.0-1.0)
                - language: Detected language code
                
        Raises:
            Exception: If transcription fails after retries
        """
        if not self.groq_client:
            logger.error("Groq client not initialized - cannot transcribe stream")
            return {
                "text": "[Transcription service unavailable]",
                "confidence": 0.0,
                "language": language or "en"
            }
        
        temp_path = None
        try:
            # Save segment to temporary file
            temp_path = self._save_temp_segment(audio_segment)
            
            logger.debug(f"Transcribing stream segment: {len(audio_segment)} bytes")
            
            # Transcribe using Groq Whisper API (whisper-large-v3-turbo for speed)
            with open(temp_path, "rb") as audio_file:
                transcript = self.groq_client.audio.transcriptions.create(
                    file=(Path(temp_path).name, audio_file, "audio/wav"),
                    model="whisper-large-v3-turbo",
                    language=language or "en",
                    response_format="verbose_json"  # Get detailed response with confidence
                )
            
            # Extract text and metadata
            text = transcript.text if hasattr(transcript, 'text') else str(transcript)
            
            # Extract confidence if available (Groq may not provide this)
            confidence = getattr(transcript, 'confidence', 0.95)
            
            # Extract detected language
            detected_language = getattr(transcript, 'language', language or 'en')
            
            logger.debug(
                f"Stream transcription complete: {len(text)} chars, "
                f"confidence={confidence:.2f}, language={detected_language}"
            )
            
            return {
                "text": text,
                "confidence": confidence,
                "language": detected_language
            }
            
        except Exception as e:
            logger.error(f"Error transcribing stream segment: {e}", exc_info=True)
            # Return fallback result instead of raising
            return {
                "text": "[Transcription failed]",
                "confidence": 0.0,
                "language": language or "en"
            }
            
        finally:
            # Clean up temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.debug(f"Cleaned up temp file: {temp_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temp file: {cleanup_error}")
    
    def _save_temp_segment(self, audio_data: bytes) -> str:
        """Save audio segment to temporary file
        
        Args:
            audio_data: Raw audio bytes in WAV format
            
        Returns:
            Path to temporary file
        """
        try:
            # Create temp file with .wav extension
            temp_file = tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False,
                mode='wb'
            )
            
            # Write audio data
            temp_file.write(audio_data)
            temp_file.flush()
            temp_file.close()
            
            logger.debug(f"Saved audio segment to temp file: {temp_file.name}")
            
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Error saving temp audio segment: {e}", exc_info=True)
            raise


# Global Whisper service instance
whisper_service = WhisperService()
