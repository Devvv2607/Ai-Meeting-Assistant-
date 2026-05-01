"""Tests for language detection service.

This module contains unit tests for the LanguageDetector service,
including tests for language detection, confidence scoring, and
error handling.
"""

import pytest
import io
from unittest.mock import Mock, patch, MagicMock
from backend.app.services.language_detector import LanguageDetector


class TestLanguageDetector:
    """Test suite for LanguageDetector service."""
    
    @pytest.fixture
    def mock_groq_client(self):
        """Create a mock Groq client."""
        client = Mock()
        return client
    
    @pytest.fixture
    def detector(self, mock_groq_client):
        """Create LanguageDetector instance with mock client."""
        return LanguageDetector(groq_client=mock_groq_client)
    
    def test_initialization_with_client(self, mock_groq_client):
        """Test LanguageDetector initializes with provided client."""
        detector = LanguageDetector(groq_client=mock_groq_client)
        assert detector.groq_client == mock_groq_client
    
    def test_supported_languages(self, detector):
        """Test that all required languages are supported."""
        supported = detector.get_supported_languages()
        
        # Verify all required languages are present
        assert 'en' in supported
        assert 'hi' in supported
        assert 'mr' in supported
        assert 'gu' in supported
        assert 'ta' in supported
        
        # Verify language names
        assert supported['en'] == 'English'
        assert supported['hi'] == 'Hindi'
        assert supported['mr'] == 'Marathi'
        assert supported['gu'] == 'Gujarati'
        assert supported['ta'] == 'Tamil'
    
    def test_is_supported_returns_true_for_supported_languages(self, detector):
        """Test is_supported returns True for supported languages."""
        assert detector.is_supported('en') is True
        assert detector.is_supported('hi') is True
        assert detector.is_supported('mr') is True
        assert detector.is_supported('gu') is True
        assert detector.is_supported('ta') is True
    
    def test_is_supported_returns_false_for_unsupported_languages(self, detector):
        """Test is_supported returns False for unsupported languages."""
        assert detector.is_supported('fr') is False
        assert detector.is_supported('de') is False
        assert detector.is_supported('es') is False
    
    def test_detect_language_with_english_audio(self, detector, mock_groq_client):
        """Test language detection with English audio."""
        # Mock Whisper API response
        mock_response = Mock()
        mock_response.language = 'en'
        mock_response.text = 'This is a test transcription with sufficient length'
        
        mock_groq_client.audio.transcriptions.create.return_value = mock_response
        
        # Create sample audio data
        audio_data = b'fake_audio_data' * 100
        
        # Detect language
        result = detector.detect_language(audio_data, 'wav')
        
        # Verify result
        assert result['language'] == 'en'
        assert result['language_name'] == 'English'
        assert result['confidence'] > 0.0
        assert result['supported'] is True
    
    def test_detect_language_with_hindi_audio(self, detector, mock_groq_client):
        """Test language detection with Hindi audio."""
        # Mock Whisper API response
        mock_response = Mock()
        mock_response.language = 'hi'
        mock_response.text = 'यह एक परीक्षण प्रतिलेखन है जिसमें पर्याप्त लंबाई है'
        
        mock_groq_client.audio.transcriptions.create.return_value = mock_response
        
        # Create sample audio data
        audio_data = b'fake_audio_data' * 100
        
        # Detect language
        result = detector.detect_language(audio_data, 'wav')
        
        # Verify result
        assert result['language'] == 'hi'
        assert result['language_name'] == 'Hindi'
        assert result['confidence'] > 0.0
        assert result['supported'] is True
    
    def test_detect_language_with_marathi_audio(self, detector, mock_groq_client):
        """Test language detection with Marathi audio."""
        # Mock Whisper API response
        mock_response = Mock()
        mock_response.language = 'mr'
        mock_response.text = 'ही एक चाचणी प्रतिलेखन आहे ज्यामध्ये पुरेशी लांबी आहे'
        
        mock_groq_client.audio.transcriptions.create.return_value = mock_response
        
        # Create sample audio data
        audio_data = b'fake_audio_data' * 100
        
        # Detect language
        result = detector.detect_language(audio_data, 'wav')
        
        # Verify result
        assert result['language'] == 'mr'
        assert result['language_name'] == 'Marathi'
        assert result['supported'] is True
    
    def test_detect_language_with_gujarati_audio(self, detector, mock_groq_client):
        """Test language detection with Gujarati audio."""
        # Mock Whisper API response
        mock_response = Mock()
        mock_response.language = 'gu'
        mock_response.text = 'આ એક પરીક્ષણ પ્રતિલેખન છે જેમાં પૂરતી લંબાઈ છે'
        
        mock_groq_client.audio.transcriptions.create.return_value = mock_response
        
        # Create sample audio data
        audio_data = b'fake_audio_data' * 100
        
        # Detect language
        result = detector.detect_language(audio_data, 'wav')
        
        # Verify result
        assert result['language'] == 'gu'
        assert result['language_name'] == 'Gujarati'
        assert result['supported'] is True
    
    def test_detect_language_with_tamil_audio(self, detector, mock_groq_client):
        """Test language detection with Tamil audio."""
        # Mock Whisper API response
        mock_response = Mock()
        mock_response.language = 'ta'
        mock_response.text = 'இது போதுமான நீளம் கொண்ட ஒரு சோதனை படியெடுப்பு ஆகும்'
        
        mock_groq_client.audio.transcriptions.create.return_value = mock_response
        
        # Create sample audio data
        audio_data = b'fake_audio_data' * 100
        
        # Detect language
        result = detector.detect_language(audio_data, 'wav')
        
        # Verify result
        assert result['language'] == 'ta'
        assert result['language_name'] == 'Tamil'
        assert result['supported'] is True
    
    def test_detect_language_with_unsupported_language(self, detector, mock_groq_client):
        """Test language detection with unsupported language."""
        # Mock Whisper API response with French
        mock_response = Mock()
        mock_response.language = 'fr'
        mock_response.text = 'Ceci est une transcription de test avec une longueur suffisante'
        
        mock_groq_client.audio.transcriptions.create.return_value = mock_response
        
        # Create sample audio data
        audio_data = b'fake_audio_data' * 100
        
        # Detect language
        result = detector.detect_language(audio_data, 'wav')
        
        # Verify result
        assert result['language'] == 'fr'
        assert result['supported'] is False
    
    def test_detect_language_with_high_confidence(self, detector, mock_groq_client):
        """Test language detection returns high confidence for long text."""
        # Mock Whisper API response with long text (>100 chars for 0.95 confidence)
        mock_response = Mock()
        mock_response.language = 'en'
        # Create text that's definitely over 100 characters
        long_text = 'This is a very long transcription with sufficient content to ensure high confidence score. ' * 2
        mock_response.text = long_text
        
        mock_groq_client.audio.transcriptions.create.return_value = mock_response
        
        # Create sample audio data
        audio_data = b'fake_audio_data' * 100
        
        # Detect language
        result = detector.detect_language(audio_data, 'wav')
        
        # Verify high confidence (should be 0.95 for text > 100 chars)
        assert result['confidence'] >= 0.90
    
    def test_detect_language_with_low_confidence(self, detector, mock_groq_client):
        """Test language detection returns lower confidence for short text."""
        # Mock Whisper API response with short text
        mock_response = Mock()
        mock_response.language = 'en'
        mock_response.text = 'Hi'
        
        mock_groq_client.audio.transcriptions.create.return_value = mock_response
        
        # Create sample audio data
        audio_data = b'fake_audio_data' * 100
        
        # Detect language
        result = detector.detect_language(audio_data, 'wav')
        
        # Verify lower confidence
        assert result['confidence'] < 0.85
    
    def test_detect_language_with_empty_audio(self, detector):
        """Test language detection with empty audio data."""
        result = detector.detect_language(b'', 'wav')
        
        # Should return fallback result
        assert result['language'] == 'en'
        assert result['confidence'] == 0.0
        assert result['supported'] is True
    
    def test_detect_language_with_api_error(self, detector, mock_groq_client):
        """Test language detection handles API errors gracefully."""
        # Mock API error
        mock_groq_client.audio.transcriptions.create.side_effect = Exception(
            "API error"
        )
        
        # Create sample audio data
        audio_data = b'fake_audio_data' * 100
        
        # Detect language
        result = detector.detect_language(audio_data, 'wav')
        
        # Should return fallback result
        assert result['language'] == 'en'
        assert result['confidence'] == 0.0
        assert result['supported'] is True
    
    def test_detect_language_without_groq_client(self):
        """Test language detection without initialized Groq client."""
        detector = LanguageDetector(groq_client=None)
        
        # Create sample audio data
        audio_data = b'fake_audio_data' * 100
        
        # Detect language
        result = detector.detect_language(audio_data, 'wav')
        
        # Should return fallback result
        assert result['language'] == 'en'
        assert result['confidence'] == 0.0
        assert result['supported'] is True
    
    def test_detect_language_with_explicit_confidence(self, detector, mock_groq_client):
        """Test language detection uses explicit confidence when available."""
        # Mock Whisper API response with explicit confidence
        mock_response = Mock()
        mock_response.language = 'en'
        mock_response.text = 'Test'
        mock_response.confidence = 0.92
        
        mock_groq_client.audio.transcriptions.create.return_value = mock_response
        
        # Create sample audio data
        audio_data = b'fake_audio_data' * 100
        
        # Detect language
        result = detector.detect_language(audio_data, 'wav')
        
        # Verify explicit confidence is used
        assert result['confidence'] == 0.92
    
    def test_detect_language_cleans_up_temp_file(self, detector, mock_groq_client):
        """Test language detection cleans up temporary files."""
        # Mock Whisper API response
        mock_response = Mock()
        mock_response.language = 'en'
        mock_response.text = 'Test transcription'
        
        mock_groq_client.audio.transcriptions.create.return_value = mock_response
        
        # Create sample audio data
        audio_data = b'fake_audio_data' * 100
        
        # Detect language
        with patch('os.path.exists', return_value=True) as mock_exists, \
             patch('os.remove') as mock_remove:
            result = detector.detect_language(audio_data, 'wav')
            
            # Verify temp file was cleaned up
            assert mock_remove.called
    
    @pytest.mark.asyncio
    async def test_detect_language_async(self, detector, mock_groq_client):
        """Test async language detection."""
        # Mock Whisper API response
        mock_response = Mock()
        mock_response.language = 'en'
        mock_response.text = 'Test transcription'
        
        mock_groq_client.audio.transcriptions.create.return_value = mock_response
        
        # Create sample audio data
        audio_data = b'fake_audio_data' * 100
        
        # Detect language asynchronously
        result = await detector.detect_language_async(audio_data, 'wav')
        
        # Verify result
        assert result['language'] == 'en'
        assert result['supported'] is True
    
    def test_detect_language_with_different_audio_formats(self, detector, mock_groq_client):
        """Test language detection with different audio formats."""
        # Mock Whisper API response
        mock_response = Mock()
        mock_response.language = 'en'
        mock_response.text = 'Test transcription'
        
        mock_groq_client.audio.transcriptions.create.return_value = mock_response
        
        # Create sample audio data
        audio_data = b'fake_audio_data' * 100
        
        # Test with different formats
        for audio_format in ['wav', 'mp3', 'webm', 'ogg']:
            result = detector.detect_language(audio_data, audio_format)
            assert result['language'] == 'en'
            assert result['supported'] is True


class TestLanguageDetectorIntegration:
    """Integration tests for LanguageDetector with real audio samples."""
    
    @pytest.fixture
    def detector_with_real_client(self):
        """Create LanguageDetector with real Groq client (if available)."""
        try:
            from groq import Groq
            from app.config import settings
            
            if not settings.GEMINI_API_KEY:
                pytest.skip("GEMINI_API_KEY not configured")
            
            client = Groq(api_key=settings.GEMINI_API_KEY)
            return LanguageDetector(groq_client=client)
        except Exception as e:
            pytest.skip(f"Could not initialize Groq client: {e}")
    
    def test_detect_language_with_real_audio(self, detector_with_real_client):
        """Test language detection with real audio (if available).
        
        This test is skipped if no real audio samples are available.
        """
        pytest.skip("Real audio samples not available in test environment")
