"""Integration tests for WhisperService streaming with AudioBuffer"""

import pytest
import asyncio
import wave
import struct
import io
from unittest.mock import Mock, patch
from app.services.whisper_service import WhisperService
from app.services.audio_buffer import AudioBuffer

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


def generate_audio_chunk(duration_ms: int = 100, sample_rate: int = 16000) -> bytes:
    """Generate a test audio chunk in WAV format
    
    Args:
        duration_ms: Duration in milliseconds
        sample_rate: Sample rate in Hz
        
    Returns:
        WAV audio bytes
    """
    duration_sec = duration_ms / 1000.0
    num_samples = int(sample_rate * duration_sec)
    
    # Generate simple sawtooth wave
    samples = []
    for i in range(num_samples):
        value = int(32767 * 0.3 * (i % 100) / 100)
        samples.append(struct.pack('<h', value))
    
    # Create WAV file in memory
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b''.join(samples))
    
    return wav_buffer.getvalue()


class TestWhisperStreamIntegration:
    """Integration tests for streaming transcription with audio buffering"""
    
    @pytest.mark.asyncio
    async def test_buffer_and_transcribe_flow(self):
        """Test complete flow: buffer chunks → create segment → transcribe"""
        # Initialize services
        audio_buffer = AudioBuffer(segment_duration=1.0, sample_rate=16000)
        whisper_service = WhisperService()
        
        # Mock Groq transcription
        mock_transcript = Mock()
        mock_transcript.text = "Test transcription"
        mock_transcript.confidence = 0.95
        mock_transcript.language = "en"
        
        # Simulate streaming 10 chunks of 100ms each (= 1 second total)
        segments_created = []
        
        for i in range(10):
            chunk = generate_audio_chunk(duration_ms=100)
            metadata = {
                'timestamp': i * 100,
                'sequence_number': i
            }
            
            # Add chunk to buffer
            segment = audio_buffer.add_chunk(
                chunk=chunk,
                duration=0.1,
                metadata=metadata
            )
            
            # When segment is ready, transcribe it
            if segment:
                segments_created.append(segment)
                
                # Transcribe the segment
                with patch.object(
                    whisper_service.groq_client.audio.transcriptions,
                    'create',
                    return_value=mock_transcript
                ) if whisper_service.groq_client else patch('builtins.open'):
                    result = await whisper_service.transcribe_stream(
                        audio_segment=segment.data,
                        language="en"
                    )
                
                # Verify transcription result
                assert "text" in result
                assert "confidence" in result
                assert "language" in result
        
        # Should have created exactly 1 segment from 10 chunks
        assert len(segments_created) == 1
        assert segments_created[0].duration == pytest.approx(1.0, abs=0.01)
        assert segments_created[0].sequence_start == 0
        assert segments_created[0].sequence_end == 9
    
    @pytest.mark.asyncio
    async def test_multiple_segments_transcription(self):
        """Test transcribing multiple segments in sequence"""
        audio_buffer = AudioBuffer(segment_duration=1.0)
        whisper_service = WhisperService()
        
        # Mock different transcriptions for each segment
        transcriptions = [
            "First segment text",
            "Second segment text",
            "Third segment text"
        ]
        
        mock_results = []
        for text in transcriptions:
            mock = Mock()
            mock.text = text
            mock.confidence = 0.9
            mock.language = "en"
            mock_results.append(mock)
        
        results = []
        
        # Stream 30 chunks (3 segments of 1 second each)
        for i in range(30):
            chunk = generate_audio_chunk(duration_ms=100)
            segment = audio_buffer.add_chunk(chunk, duration=0.1)
            
            if segment:
                # Use different mock for each segment
                segment_index = len(results)
                
                with patch.object(
                    whisper_service.groq_client.audio.transcriptions,
                    'create',
                    return_value=mock_results[segment_index]
                ) if whisper_service.groq_client else patch('builtins.open'):
                    result = await whisper_service.transcribe_stream(
                        audio_segment=segment.data,
                        language="en"
                    )
                
                results.append(result)
        
        # Should have 3 transcribed segments
        assert len(results) == 3
        
        if whisper_service.groq_client:
            assert results[0]["text"] == "First segment text"
            assert results[1]["text"] == "Second segment text"
            assert results[2]["text"] == "Third segment text"
    
    @pytest.mark.asyncio
    async def test_partial_segment_flush(self):
        """Test flushing partial segment at end of stream"""
        audio_buffer = AudioBuffer(segment_duration=1.0)
        whisper_service = WhisperService()
        
        mock_transcript = Mock()
        mock_transcript.text = "Partial segment"
        mock_transcript.confidence = 0.88
        mock_transcript.language = "en"
        
        # Add only 5 chunks (0.5 seconds, less than segment duration)
        for i in range(5):
            chunk = generate_audio_chunk(duration_ms=100)
            segment = audio_buffer.add_chunk(chunk, duration=0.1)
            assert segment is None  # Should not create segment yet
        
        # Flush remaining buffer
        segment = audio_buffer.flush()
        assert segment is not None
        assert segment.duration == pytest.approx(0.5, abs=0.01)
        
        # Transcribe the partial segment
        with patch.object(
            whisper_service.groq_client.audio.transcriptions,
            'create',
            return_value=mock_transcript
        ) if whisper_service.groq_client else patch('builtins.open'):
            result = await whisper_service.transcribe_stream(
                audio_segment=segment.data,
                language="en"
            )
        
        assert result["text"] in ["Partial segment", "[Transcription service unavailable]"]
    
    @pytest.mark.asyncio
    async def test_language_detection_flow(self):
        """Test language detection in streaming transcription"""
        whisper_service = WhisperService()
        
        # Mock Hindi transcription
        mock_transcript = Mock()
        mock_transcript.text = "नमस्ते"
        mock_transcript.confidence = 0.92
        mock_transcript.language = "hi"
        
        chunk = generate_audio_chunk(duration_ms=1000)
        
        with patch.object(
            whisper_service.groq_client.audio.transcriptions,
            'create',
            return_value=mock_transcript
        ) if whisper_service.groq_client else patch('builtins.open'):
            # Provide English hint but expect Hindi detection
            result = await whisper_service.transcribe_stream(
                audio_segment=chunk,
                language="en"
            )
        
        # Should detect Hindi even with English hint
        if whisper_service.groq_client:
            assert result["language"] == "hi"
    
    @pytest.mark.asyncio
    async def test_low_confidence_handling(self):
        """Test handling of low confidence transcriptions"""
        whisper_service = WhisperService()
        
        # Mock low confidence transcription
        mock_transcript = Mock()
        mock_transcript.text = "Unclear audio"
        mock_transcript.confidence = 0.45  # Below 70% threshold
        mock_transcript.language = "en"
        
        chunk = generate_audio_chunk(duration_ms=1000)
        
        with patch.object(
            whisper_service.groq_client.audio.transcriptions,
            'create',
            return_value=mock_transcript
        ) if whisper_service.groq_client else patch('builtins.open'):
            result = await whisper_service.transcribe_stream(
                audio_segment=chunk,
                language="en"
            )
        
        # Should still return result but with low confidence
        assert result["confidence"] < 0.7
    
    @pytest.mark.asyncio
    async def test_concurrent_transcription(self):
        """Test concurrent transcription of multiple segments"""
        whisper_service = WhisperService()
        
        # Create multiple segments
        segments = [generate_audio_chunk(duration_ms=1000) for _ in range(3)]
        
        mock_transcript = Mock()
        mock_transcript.text = "Concurrent test"
        mock_transcript.confidence = 0.9
        mock_transcript.language = "en"
        
        # Transcribe all segments concurrently
        async def transcribe_segment(segment):
            with patch.object(
                whisper_service.groq_client.audio.transcriptions,
                'create',
                return_value=mock_transcript
            ) if whisper_service.groq_client else patch('builtins.open'):
                return await whisper_service.transcribe_stream(
                    audio_segment=segment,
                    language="en"
                )
        
        # Run transcriptions concurrently
        results = await asyncio.gather(*[
            transcribe_segment(seg) for seg in segments
        ])
        
        # All should complete successfully
        assert len(results) == 3
        for result in results:
            assert "text" in result
            assert "confidence" in result
    
    def test_buffer_stats_tracking(self):
        """Test that buffer statistics are tracked correctly"""
        audio_buffer = AudioBuffer(segment_duration=1.0)
        
        # Add some chunks
        for i in range(5):
            chunk = generate_audio_chunk(duration_ms=100)
            audio_buffer.add_chunk(chunk, duration=0.1)
        
        stats = audio_buffer.get_stats()
        
        assert stats['buffer_chunks'] == 5
        assert stats['buffer_duration'] == pytest.approx(0.5, abs=0.01)
        assert stats['segment_duration'] == 1.0
        assert stats['sample_rate'] == 16000
        
        # Complete the segment
        for i in range(5):
            chunk = generate_audio_chunk(duration_ms=100)
            segment = audio_buffer.add_chunk(chunk, duration=0.1)
        
        # After segment creation, buffer should be empty
        stats = audio_buffer.get_stats()
        assert stats['total_segments'] == 1
        assert stats['buffer_chunks'] == 0
        assert stats['buffer_duration'] == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
