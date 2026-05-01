"""Language detection service for live meeting audio.

This module provides language detection capabilities using Whisper's
built-in language detection. It analyzes audio segments to identify
the spoken language and confidence level.
"""

import io
import logging
import tempfile
import os
from typing import Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class LanguageDetector:
    """Service for detecting spoken language in audio segments.
    
    This service uses Whisper's built-in language detection to identify
    the language being spoken in audio segments. It supports multiple
    languages including English, Hindi, Marathi, Gujarati, and Tamil.
    
    Attributes:
        groq_client: Groq API client for Whisper access
        supported_languages: Set of supported language codes
    """
    
    # Supported languages with their codes
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'hi': 'Hindi',
        'mr': 'Marathi',
        'gu': 'Gujarati',
        'ta': 'Tamil'
    }
    
    def __init__(self, groq_client=None):
        """Initialize LanguageDetector.
        
        Args:
            groq_client: Optional Groq client instance. If not provided,
                        will be initialized from settings.
        """
        self.groq_client = groq_client
        
        if self.groq_client is None:
            self._init_groq_client()
        
        logger.info(
            f"LanguageDetector initialized with support for: "
            f"{', '.join(self.SUPPORTED_LANGUAGES.values())}"
        )
    
    def _init_groq_client(self):
        """Initialize Groq client from settings."""
        try:
            from groq import Groq
            from app.config import settings
            
            api_key = settings.GEMINI_API_KEY
            
            if not api_key or api_key == "":
                logger.error(
                    "GEMINI_API_KEY not configured - language detection will not work"
                )
                self.groq_client = None
                return
            
            self.groq_client = Groq(api_key=api_key)
            logger.info("Groq client initialized for language detection")
            
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}", exc_info=True)
            self.groq_client = None
    
    def detect_language(
        self,
        audio_data: bytes,
        audio_format: str = 'wav'
    ) -> Dict[str, any]:
        """Detect language from audio segment.
        
        This method analyzes an audio segment and returns the detected
        language code and confidence score. It uses Whisper's built-in
        language detection via the Groq API.
        
        Args:
            audio_data: Raw audio bytes (WAV format recommended)
            audio_format: Audio format ('wav', 'mp3', 'webm', etc.)
        
        Returns:
            Dictionary with:
                - language: Detected language code (e.g., 'en', 'hi')
                - language_name: Full language name (e.g., 'English')
                - confidence: Confidence score (0.0-1.0)
                - supported: Whether the language is in supported list
        
        Example:
            >>> detector = LanguageDetector()
            >>> result = detector.detect_language(audio_bytes)
            >>> print(result)
            {
                'language': 'en',
                'language_name': 'English',
                'confidence': 0.95,
                'supported': True
            }
        """
        if not self.groq_client:
            logger.error("Groq client not initialized - cannot detect language")
            return self._get_fallback_result()
        
        if not audio_data:
            logger.warning("Empty audio data provided")
            return self._get_fallback_result()
        
        temp_path = None
        try:
            # Save audio to temporary file
            temp_path = self._save_temp_audio(audio_data, audio_format)
            
            logger.debug(
                f"Detecting language from audio: {len(audio_data)} bytes"
            )
            
            # Use Groq Whisper API with language detection
            # The API returns language information when we don't specify a language
            with open(temp_path, "rb") as audio_file:
                transcript = self.groq_client.audio.transcriptions.create(
                    file=(Path(temp_path).name, audio_file, f"audio/{audio_format}"),
                    model="whisper-large-v3-turbo",
                    response_format="verbose_json"  # Get detailed response
                )
            
            # Extract language information
            detected_language = getattr(transcript, 'language', 'en')
            
            # Whisper doesn't provide confidence directly, but we can infer it
            # from the transcription quality and language probability
            # For now, we'll use a heuristic based on text length and quality
            confidence = self._estimate_confidence(transcript)
            
            # Check if language is supported
            is_supported = detected_language in self.SUPPORTED_LANGUAGES
            language_name = self.SUPPORTED_LANGUAGES.get(
                detected_language,
                detected_language.upper()
            )
            
            result = {
                'language': detected_language,
                'language_name': language_name,
                'confidence': confidence,
                'supported': is_supported
            }
            
            logger.info(
                f"Language detected: {language_name} ({detected_language}) "
                f"with confidence {confidence:.2f}"
            )
            
            if not is_supported:
                logger.warning(
                    f"Detected language '{language_name}' is not in supported list. "
                    f"Supported: {', '.join(self.SUPPORTED_LANGUAGES.values())}"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error detecting language: {e}", exc_info=True)
            return self._get_fallback_result()
            
        finally:
            # Clean up temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.debug(f"Cleaned up temp file: {temp_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temp file: {cleanup_error}")
    
    def _save_temp_audio(self, audio_data: bytes, audio_format: str) -> str:
        """Save audio data to temporary file.
        
        Args:
            audio_data: Raw audio bytes
            audio_format: Audio format extension
        
        Returns:
            Path to temporary file
        """
        try:
            # Create temp file with appropriate extension
            temp_file = tempfile.NamedTemporaryFile(
                suffix=f".{audio_format}",
                delete=False,
                mode='wb'
            )
            
            # Write audio data
            temp_file.write(audio_data)
            temp_file.flush()
            temp_file.close()
            
            logger.debug(f"Saved audio to temp file: {temp_file.name}")
            
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Error saving temp audio file: {e}", exc_info=True)
            raise
    
    def _estimate_confidence(self, transcript) -> float:
        """Estimate confidence score from transcript response.
        
        Whisper doesn't always provide a direct confidence score,
        so we estimate it based on available information.
        
        Args:
            transcript: Whisper API response object
        
        Returns:
            Estimated confidence score (0.0-1.0)
        """
        try:
            # Try to get confidence from response
            if hasattr(transcript, 'confidence'):
                confidence_val = transcript.confidence
                # Check if it's actually a number (not a Mock or other object)
                if isinstance(confidence_val, (int, float)):
                    return float(confidence_val)
            
            # If no confidence, estimate based on text quality
            text = getattr(transcript, 'text', '')
            
            # Heuristic: longer, more coherent text = higher confidence
            text_length = len(text.strip())
            
            logger.debug(f"Estimating confidence from text length: {text_length}")
            
            if text_length > 100:
                confidence = 0.95
            elif text_length > 50:
                confidence = 0.90
            elif text_length > 20:
                confidence = 0.85
            elif text_length > 5:
                confidence = 0.75
            else:
                confidence = 0.60
            
            logger.debug(f"Estimated confidence: {confidence}")
            return confidence
            
        except Exception as e:
            logger.error(f"Error estimating confidence: {e}", exc_info=True)
            return 0.80  # Default moderate confidence
    
    def _get_fallback_result(self) -> Dict[str, any]:
        """Get fallback result when detection fails.
        
        Returns:
            Dictionary with default English language result
        """
        return {
            'language': 'en',
            'language_name': 'English',
            'confidence': 0.0,
            'supported': True
        }
    
    def is_supported(self, language_code: str) -> bool:
        """Check if a language code is supported.
        
        Args:
            language_code: Language code to check (e.g., 'en', 'hi')
        
        Returns:
            True if language is supported, False otherwise
        """
        return language_code in self.SUPPORTED_LANGUAGES
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get dictionary of supported languages.
        
        Returns:
            Dictionary mapping language codes to names
        """
        return self.SUPPORTED_LANGUAGES.copy()
    
    async def detect_language_async(
        self,
        audio_data: bytes,
        audio_format: str = 'wav'
    ) -> Dict[str, any]:
        """Async version of detect_language.
        
        This method provides an async interface for language detection,
        useful for integration with async frameworks like FastAPI.
        
        Args:
            audio_data: Raw audio bytes
            audio_format: Audio format
        
        Returns:
            Dictionary with language detection results
        """
        # For now, just call the sync version
        # In the future, this could use async Groq client
        return self.detect_language(audio_data, audio_format)


# Global language detector instance
language_detector = LanguageDetector()
