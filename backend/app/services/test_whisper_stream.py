"""Tests for WhisperService streaming transcription functionality"""

import pytest
import asyncio
import os
import wave
import struct
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from app.services.whisper_service import WhisperService

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture
def sample_audio_segment():
    """Generate a sample 1-second audio segment in WAV format"""
    # Create a simple 1-second WAV file (16kHz, mono, 16-bit)
    sample_rate = 16000
    duration = 1.0
    frequency = 440  # A4 note
    
    # Generate sine wave
    samples = []
    for i in range(int(sample_rate * duration)):
        value = int(32767 * 0.3 * (i % 100) / 100)  # Simple sawtooth wave
        samples.append(struct.pack('<h', value))
    
    # Create WAV file in memory
    import io
    wav_buffer = io.BytesIO()
    
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b''.join(samples))
    
    return wav_buffer.getvalue()


@pytest.fixture
def whisper_service():
    """Create WhisperService instance for testing"""
    return WhisperService()


class TestWhisperStreamTranscription:
    """Test suite for streaming transcription functionality"""
    
    @pytest.mark.asyncio
    async def test_transcribe_stream_basic(self, whisper_service, sample_audio_segment):
        """Test basic streaming transcription with valid audio"""
        # Mock Groq client
        mock_transcript = Mock()
        mock_transcript.text = "Hello world"
        mock_transcript.confidence = 0.95
        mock_transcript.language = "en"
        
        with patch.object(
            whisper_service.groq_client.audio.transcriptions,
            'create',
            return_value=mock_transcript
        ) if whisper_service.groq_client else patch('builtins.open'):
            result = await whisper_service.transcribe_stream(
                audio_segment=sample_audio_segment,
                language="en"
            )
        
        # Verify result structure
        assert "text" in result
        assert "confidence" in result
        assert "language" in result
        
        # If Groq is available, verify values
        if whisper_service.groq_client:
            assert result["text"] == "Hello world"
            assert result["confidence"] == 0.95
            assert result["language"] == "en"
    
    @pytest.mark.asyncio
    async def test_transcribe_stream_no_language_hint(self, whisper_service, sample_audio_segment):
        """Test streaming transcription without language hint"""
        mock_transcript = Mock()
        mock_transcript.text = "Test transcription"
        mock_transcript.language = "en"
        
        with patch.object(
            whisper_service.groq_client.audio.transcriptions,
            'create',
            return_value=mock_transcript
        ) if whisper_service.groq_client else patch('builtins.open'):
            result = await whisper_service.transcribe_stream(
                audio_segment=sample_audio_segment
            )
        
        assert result["language"] in ["en", "en"]  # Should default to 'en'
    
    @pytest.mark.asyncio
    async def test_transcribe_stream_multilingual(self, whisper_service, sample_audio_segment):
        """Test streaming transcription with Hindi language hint"""
        mock_transcript = Mock()
        mock_transcript.text = "नमस्ते दुनिया"
        mock_transcript.confidence = 0.92
        mock_transcript.language = "hi"
        
        with patch.object(
            whisper_service.groq_client.audio.transcriptions,
            'create',
            return_value=mock_transcript
        ) if whisper_service.groq_client else patch('builtins.open'):
            result = await whisper_service.transcribe_stream(
                audio_segment=sample_audio_segment,
                language="hi"
            )
        
        if whisper_service.groq_client:
            assert result["language"] == "hi"
    
    @pytest.mark.asyncio
    async def test_transcribe_stream_error_handling(self, whisper_service, sample_audio_segment):
        """Test error handling when transcription fails"""
        # Mock Groq client to raise an exception
        with patch.object(
            whisper_service.groq_client.audio.transcriptions,
            'create',
            side_effect=Exception("API Error")
        ) if whisper_service.groq_client else patch('builtins.open'):
            result = await whisper_service.transcribe_stream(
                audio_segment=sample_audio_segment,
                language="en"
            )
        
        # Should return fallback result instead of raising
        assert result["text"] == "[Transcription failed]"
        assert result["confidence"] == 0.0
    
    @pytest.mark.asyncio
    async def test_transcribe_stream_no_groq_client(self, sample_audio_segment):
        """Test behavior when Groq client is not initialized"""
        # Create service without Groq client
        service = WhisperService()
        service.groq_client = None
        
        result = await service.transcribe_stream(
            audio_segment=sample_audio_segment,
            language="en"
        )
        
        # Should return unavailable message
        assert result["text"] == "[Transcription service unavailable]"
        assert result["confidence"] == 0.0
        assert result["language"] == "en"
    
    def test_save_temp_segment(self, whisper_service, sample_audio_segment):
        """Test temporary file creation and cleanup"""
        # Save segment
        temp_path = whisper_service._save_temp_segment(sample_audio_segment)
        
        try:
            # Verify file exists
            assert os.path.exists(temp_path)
            assert temp_path.endswith('.wav')
            
            # Verify file size
            file_size = os.path.getsize(temp_path)
            assert file_size == len(sample_audio_segment)
            
            # Verify file content
            with open(temp_path, 'rb') as f:
                content = f.read()
                assert content == sample_audio_segment
        
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_save_temp_segment_empty_data(self, whisper_service):
        """Test saving empty audio data"""
        # Should still create file but with 0 bytes
        temp_path = whisper_service._save_temp_segment(b'')
        
        try:
            assert os.path.exists(temp_path)
            assert os.path.getsize(temp_path) == 0
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    @pytest.mark.asyncio
    async def test_transcribe_stream_temp_file_cleanup(self, whisper_service, sample_audio_segment):
        """Test that temporary files are cleaned up after transcription"""
        temp_files_before = set(os.listdir(tempfile.gettempdir()))
        
        mock_transcript = Mock()
        mock_transcript.text = "Test"
        mock_transcript.confidence = 0.9
        mock_transcript.language = "en"
        
        with patch.object(
            whisper_service.groq_client.audio.transcriptions,
            'create',
            return_value=mock_transcript
        ) if whisper_service.groq_client else patch('builtins.open'):
            await whisper_service.transcribe_stream(
                audio_segment=sample_audio_segment,
                language="en"
            )
        
        # Give a moment for cleanup
        await asyncio.sleep(0.1)
        
        temp_files_after = set(os.listdir(tempfile.gettempdir()))
        
        # No new temp files should remain
        new_files = temp_files_after - temp_files_before
        wav_files = [f for f in new_files if f.endswith('.wav')]
        assert len(wav_files) == 0, f"Temp files not cleaned up: {wav_files}"
    
    @pytest.mark.asyncio
    async def test_transcribe_stream_confidence_score(self, whisper_service, sample_audio_segment):
        """Test that confidence scores are properly extracted"""
        # Test with confidence
        mock_transcript = Mock()
        mock_transcript.text = "High confidence"
        mock_transcript.confidence = 0.98
        mock_transcript.language = "en"
        
        with patch.object(
            whisper_service.groq_client.audio.transcriptions,
            'create',
            return_value=mock_transcript
        ) if whisper_service.groq_client else patch('builtins.open'):
            result = await whisper_service.transcribe_stream(
                audio_segment=sample_audio_segment,
                language="en"
            )
        
        if whisper_service.groq_client:
            assert 0.0 <= result["confidence"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_transcribe_stream_detected_language(self, whisper_service, sample_audio_segment):
        """Test that detected language is returned"""
        mock_transcript = Mock()
        mock_transcript.text = "Bonjour"
        mock_transcript.confidence = 0.95
        mock_transcript.language = "fr"
        
        with patch.object(
            whisper_service.groq_client.audio.transcriptions,
            'create',
            return_value=mock_transcript
        ) if whisper_service.groq_client else patch('builtins.open'):
            result = await whisper_service.transcribe_stream(
                audio_segment=sample_audio_segment,
                language="en"  # Hint English but detect French
            )
        
        if whisper_service.groq_client:
            # Should return detected language, not hint
            assert result["language"] == "fr"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
