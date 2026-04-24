"""Service for translating transcripts to multiple languages"""

from typing import List, Dict, Optional
import logging
import json
from datetime import datetime, timedelta
from app.models.transcript import Transcript
from app.config import settings
from sqlalchemy.orm import Session
import requests

logger = logging.getLogger(__name__)

# Supported languages
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'zh': 'Chinese (Simplified)',
    'ja': 'Japanese',
    'ko': 'Korean',
    'ar': 'Arabic',
    'hi': 'Hindi'
}


class TranslationService:
    """Service for translating transcripts"""
    
    def __init__(self):
        """Initialize translation service"""
        # Using free translation API (MyMemory)
        self.api_url = "https://api.mymemory.translated.net/get"
        logger.info("✓ Translation service initialized (MyMemory API)")
    
    def translate_transcript(
        self,
        transcripts: List[Transcript],
        target_language: str,
        cache: Optional[Dict] = None
    ) -> Dict:
        """Translate transcript segments to target language
        
        Args:
            transcripts: List of transcript segments
            target_language: Target language code (e.g., 'es', 'fr')
            cache: Optional cache dictionary
            
        Returns:
            Dictionary with translated segments
        """
        if target_language == 'en':
            # No translation needed for English
            return {
                'language': 'en',
                'segments': [
                    {
                        'speaker': t.speaker,
                        'text': t.text,
                        'start_time': t.start_time,
                        'end_time': t.end_time
                    }
                    for t in transcripts
                ]
            }
        
        if target_language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {target_language}")
        
        try:
            logger.info(f"Translating {len(transcripts)} segments to {target_language}")
            
            translated_segments = []
            
            for segment in transcripts:
                # Check cache first
                cache_key = f"{segment.id}_{target_language}"
                if cache and cache_key in cache:
                    translated_text = cache[cache_key]
                    logger.info(f"Using cached translation for segment {segment.id}")
                else:
                    # Translate text
                    translated_text = self.translate_text(segment.text, target_language)
                    
                    # Cache result
                    if cache is not None:
                        cache[cache_key] = translated_text
                
                translated_segments.append({
                    'speaker': segment.speaker,
                    'text': translated_text,
                    'start_time': segment.start_time,
                    'end_time': segment.end_time
                })
            
            logger.info(f"✓ Translation complete: {len(translated_segments)} segments")
            
            return {
                'language': target_language,
                'language_name': SUPPORTED_LANGUAGES.get(target_language, target_language),
                'segments': translated_segments
            }
            
        except Exception as e:
            logger.error(f"Error translating transcript: {e}", exc_info=True)
            raise
    
    def translate_text(self, text: str, target_language: str) -> str:
        """Translate single text to target language using MyMemory API
        
        Args:
            text: Text to translate
            target_language: Target language code
            
        Returns:
            Translated text
        """
        if target_language == 'en':
            return text
        
        try:
            # Limit text length for API
            if len(text) > 500:
                # Split long text into chunks
                chunks = [text[i:i+500] for i in range(0, len(text), 500)]
                translated_chunks = [self._translate_chunk(chunk, target_language) for chunk in chunks]
                return " ".join(translated_chunks)
            else:
                return self._translate_chunk(text, target_language)
        except Exception as e:
            logger.error(f"Error translating text: {e}")
            return text
    
    def _translate_chunk(self, text: str, target_language: str) -> str:
        """Translate a chunk of text
        
        Args:
            text: Text to translate
            target_language: Target language code
            
        Returns:
            Translated text
        """
        try:
            params = {
                'q': text,
                'langpair': f'en|{target_language}'
            }
            
            response = requests.get(self.api_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('responseStatus') == 200:
                return data.get('responseData', {}).get('translatedText', text)
            else:
                logger.warning(f"Translation API error: {data.get('responseStatus')}")
                return text
                
        except Exception as e:
            logger.error(f"Error in translation chunk: {e}")
            return text
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported languages
        
        Returns:
            Dictionary of language codes and names
        """
        return SUPPORTED_LANGUAGES.copy()


# Global translation service instance
translation_service = TranslationService()
