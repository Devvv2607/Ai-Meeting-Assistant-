from typing import List, Dict, Optional
import logging
from app.config import settings
import google.generativeai as genai
from pathlib import Path

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
        """Transcribe using Groq API"""
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
            
            # Read audio file
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
            
            logger.info(f"Transcription successful: {len(text)} characters")
            
            return [{
                "speaker": "Speaker 1",
                "text": text,
                "start_time": 0.0,
                "end_time": float(duration) if duration else 60.0
            }]
            
        except Exception as e:
            logger.error(f"Error transcribing audio with Groq: {e}", exc_info=True)
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


# Global Whisper service instance
whisper_service = WhisperService()
