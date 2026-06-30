from typing import List, Dict, Optional
import logging
from app.config import settings
import google.generativeai as genai
from pathlib import Path
import tempfile
import os

logger = logging.getLogger(__name__)


def _ffmpeg_bin() -> str:
    """Resolve the ffmpeg binary reliably.

    NEVER depend on a bare ``"ffmpeg"`` on PATH — that's the prod-fragility that
    silently broke the chunked path (shutil.which('ffmpeg') is None in this env).
    Order: env FFMPEG_PATH → bundled imageio-ffmpeg → PATH lookup → "ffmpeg".
    """
    env = os.getenv("FFMPEG_PATH")
    if env and os.path.exists(env):
        return env
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass
    from shutil import which
    return which("ffmpeg") or "ffmpeg"


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
            
            # Live transcription path: short timeout + single retry so a stalled
            # or rate-limited segment fails fast instead of amplifying load.
            self.groq_client = Groq(api_key=api_key, timeout=15.0, max_retries=1)
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
            return self._transcribe_groq(audio_path, language)
        else:
            return self._transcribe_gemini(audio_path)

    @staticmethod
    def _lang_kwargs(language: Optional[str]) -> dict:
        """Pass an explicit language to Groq only when one is set; otherwise omit
        it so Whisper auto-detects (forcing 'en' mistranscribes non-English audio)."""
        return {"language": language} if language else {}

    def _build_segments(self, transcript, detected_language, audio_path, time_offset: float = 0.0) -> List[Dict]:
        """Turn a Groq verbose_json response into fine-grained, timestamped segments.

        Diarization needs per-segment timestamps to align speaker turns against.
        Groq's verbose_json already returns a ``segments`` array; we surface it
        (offset by ``time_offset`` for chunked audio). Falls back to a single
        block when segments are unavailable.
        """
        text = transcript.text if hasattr(transcript, "text") else str(transcript)
        raw_segs = getattr(transcript, "segments", None) or []

        def _field(s, name):
            return s.get(name) if isinstance(s, dict) else getattr(s, name, None)

        out: List[Dict] = []
        for s in raw_segs:
            tx = _field(s, "text")
            if tx is None:
                continue
            tx = tx.strip() if isinstance(tx, str) else str(tx)
            if not tx:
                continue
            out.append({
                "speaker": "Speaker 1",
                "text": tx,
                "start_time": float(_field(s, "start") or 0.0) + time_offset,
                "end_time": float(_field(s, "end") or 0.0) + time_offset,
                "language": detected_language,
            })

        if out:
            return out

        # Fallback: single block (e.g. segments missing on some responses).
        from app.utils.audio_utils import AudioProcessor
        duration = AudioProcessor().get_duration(audio_path)
        return [{
            "speaker": "Speaker 1",
            "text": text,
            "start_time": time_offset,
            "end_time": (float(duration) if duration else 60.0) + time_offset,
            "language": detected_language,
        }]

    def _transcribe_groq(self, audio_path: str, language: Optional[str] = None) -> List[Dict]:
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
                return self._transcribe_groq_chunked(audio_path, language)
            
            # File is small enough, transcribe directly
            with open(audio_path, "rb") as audio_file:
                transcript = self.groq_client.audio.transcriptions.create(
                    file=(Path(audio_path).name, audio_file, "audio/mpeg"),
                    model="whisper-large-v3-turbo",
                    response_format="verbose_json",  # exposes detected language
                    **self._lang_kwargs(language),
                )

            logger.info(f"Received transcription from Groq")

            # Parse Groq response
            text = transcript.text if hasattr(transcript, 'text') else str(transcript)
            detected_language = getattr(transcript, "language", language) or language

            # Create segments from the transcription
            from app.utils.audio_utils import AudioProcessor
            audio_processor = AudioProcessor()
            duration = audio_processor.get_duration(audio_path)

            segments = self._build_segments(transcript, detected_language, audio_path)
            logger.info(
                f"✓ Transcription successful: {len(text)} characters, "
                f"{len(segments)} segments (language: {detected_language})"
            )
            return segments
            
        except Exception as e:
            logger.error(f"Error transcribing audio with Groq: {e}", exc_info=True)
            return self._get_fallback_transcript(audio_path)
    
    def _transcribe_groq_chunked(self, audio_path: str, language: Optional[str] = None) -> List[Dict]:
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
                # Split into INDEPENDENTLY DECODABLE chunks. The old `-c copy`
                # remux cut the compressed stream mid-frame → chunks Groq could not
                # decode. Re-encoding each segment to a standalone MP3 (libmp3lame)
                # produces self-contained, Groq-readable files. `-segment_list`
                # records each chunk's EXACT absolute start time (CSV), and
                # `-reset_timestamps 1` makes each chunk start at 0 internally so
                # Groq returns chunk-relative times we offset by that absolute start.
                segment_list = os.path.join(temp_dir, "segments.csv")
                logger.info("Splitting audio into 10-minute decodable MP3 chunks")

                cmd = [
                    _ffmpeg_bin(),
                    "-hide_banner", "-loglevel", "error",
                    "-i", audio_path,
                    "-vn",
                    "-f", "segment",
                    "-segment_time", "600",          # 10 minutes
                    "-segment_list", segment_list,    # CSV: file,abs_start,abs_end
                    "-reset_timestamps", "1",
                    "-c:a", "libmp3lame", "-b:a", "64k",
                    "-y",
                    f"{chunk_prefix}_%03d.mp3",
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode != 0:
                    logger.warning(f"ffmpeg split failed: {result.stderr}")
                    logger.info("Falling back to compression method")
                    return self._transcribe_groq_compressed(audio_path, language)

                # Parse the segment list for each chunk's EXACT absolute start (seconds).
                chunk_starts: Dict[str, float] = {}
                try:
                    with open(segment_list) as sl:
                        for line in sl:
                            parts = line.strip().split(",")
                            if len(parts) >= 2:
                                chunk_starts[os.path.basename(parts[0])] = float(parts[1])
                except Exception as e:
                    logger.warning(f"Could not parse segment list ({e}); using i*600 offsets")

                chunk_files = sorted([f for f in os.listdir(temp_dir) if f.startswith("chunk_") and f.endswith(".mp3")])
                logger.info(f"✓ Created {len(chunk_files)} decodable audio chunks")

                detected_language = language
                all_segments: List[Dict] = []
                for i, chunk_file in enumerate(chunk_files):
                    chunk_path = os.path.join(temp_dir, chunk_file)
                    # Exact absolute offset from ffmpeg's segment list (fallback i*600).
                    offset = chunk_starts.get(chunk_file, i * 600.0)
                    logger.info(f"Transcribing chunk {i+1}/{len(chunk_files)} @ abs {offset:.1f}s: {chunk_file}")

                    try:
                        with open(chunk_path, "rb") as audio_file:
                            transcript = self.groq_client.audio.transcriptions.create(
                                file=(chunk_file, audio_file, "audio/mpeg"),
                                model="whisper-large-v3-turbo",
                                response_format="verbose_json",
                                **self._lang_kwargs(language),
                            )

                        if not detected_language:
                            detected_language = getattr(transcript, "language", None)
                        chunk_segs = self._build_segments(
                            transcript, detected_language, chunk_path, time_offset=offset
                        )
                        all_segments.extend(chunk_segs)
                        text = transcript.text if hasattr(transcript, 'text') else str(transcript)
                        logger.info(f"✓ Chunk {i+1} transcribed: {len(text)} chars, {len(chunk_segs)} segments")

                    except Exception as chunk_error:
                        logger.error(f"Error transcribing chunk {i+1}: {chunk_error}")

                from app.utils.audio_utils import AudioProcessor
                duration = AudioProcessor().get_duration(audio_path)
                logger.info(f"✓ Chunked transcription complete: {len(all_segments)} segments total")

                if all_segments:
                    return all_segments
                return [{
                    "speaker": "Speaker 1",
                    "text": "",
                    "start_time": 0.0,
                    "end_time": float(duration) if duration else 60.0,
                    "language": detected_language,
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
            return self._transcribe_groq_compressed(audio_path, language)
    
    def _transcribe_groq_compressed(self, audio_path: str, language: Optional[str] = None) -> List[Dict]:
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
                    _ffmpeg_bin(),
                    "-hide_banner", "-loglevel", "error",
                    "-i", audio_path,
                    "-vn",
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
                        response_format="verbose_json",
                        **self._lang_kwargs(language),
                    )

                text = transcript.text if hasattr(transcript, 'text') else str(transcript)
                detected_language = getattr(transcript, "language", language) or language

                segments = self._build_segments(transcript, detected_language, audio_path)
                logger.info(
                    f"✓ Compressed transcription successful: {len(text)} characters, "
                    f"{len(segments)} segments (language: {detected_language})"
                )
                return segments
                
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
                    response_format="verbose_json",  # Get detailed response with confidence
                    **self._lang_kwargs(language),  # auto-detect when unset
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
