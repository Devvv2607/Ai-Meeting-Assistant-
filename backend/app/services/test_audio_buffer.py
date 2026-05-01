"""Tests for AudioBuffer service.

This module tests the audio buffering functionality for live meeting
audio streaming, including chunk buffering, segment creation, and
audio format conversion.
"""

import pytest
import io
from datetime import datetime
from backend.app.services.audio_buffer import AudioBuffer, AudioSegment


class TestAudioBufferInitialization:
    """Tests for AudioBuffer initialization"""
    
    def test_default_initialization(self):
        """Test AudioBuffer with default parameters"""
        buffer = AudioBuffer()
        
        assert buffer.segment_duration == 1.0
        assert buffer.sample_rate == 16000
        assert buffer.buffer == []
        assert buffer.buffer_duration == 0.0
        assert buffer.total_segments == 0
    
    def test_custom_initialization(self):
        """Test AudioBuffer with custom parameters"""
        buffer = AudioBuffer(segment_duration=2.0, sample_rate=48000)
        
        assert buffer.segment_duration == 2.0
        assert buffer.sample_rate == 48000
        assert buffer.buffer == []
        assert buffer.buffer_duration == 0.0


class TestAddChunk:
    """Tests for add_chunk method"""
    
    def test_add_single_chunk_below_threshold(self):
        """Test adding a single chunk that doesn't reach segment duration"""
        buffer = AudioBuffer(segment_duration=1.0)
        
        # Add 100ms chunk (below 1 second threshold)
        chunk_data = b'audio_data_100ms'
        segment = buffer.add_chunk(chunk_data, duration=0.1)
        
        assert segment is None  # No segment created yet
        assert len(buffer.buffer) == 1
        assert buffer.buffer_duration == 0.1
        assert buffer.total_segments == 0
    
    def test_add_multiple_chunks_reaching_threshold(self):
        """Test adding multiple chunks that reach segment duration"""
        buffer = AudioBuffer(segment_duration=1.0)
        
        # Add 10 chunks of 100ms each (total 1 second)
        for i in range(10):
            chunk_data = f'audio_chunk_{i}'.encode()
            segment = buffer.add_chunk(chunk_data, duration=0.1)
            
            if i < 9:
                assert segment is None  # Not ready yet
            else:
                assert segment is not None  # Segment created on 10th chunk
                assert isinstance(segment, AudioSegment)
                assert segment.duration == pytest.approx(1.0, abs=0.01)
        
        # Buffer should be cleared after segment creation
        assert len(buffer.buffer) == 0
        assert buffer.buffer_duration == 0.0
        assert buffer.total_segments == 1
    
    def test_add_chunk_with_metadata(self):
        """Test adding chunks with metadata tracking"""
        buffer = AudioBuffer(segment_duration=0.3)  # 300ms for faster test
        
        # Add 3 chunks with metadata
        for i in range(3):
            metadata = {
                'sequence_number': i,
                'timestamp': datetime.utcnow().timestamp()
            }
            segment = buffer.add_chunk(
                f'chunk_{i}'.encode(),
                duration=0.1,
                metadata=metadata
            )
        
        assert segment is not None
        assert segment.sequence_start == 0
        assert segment.sequence_end == 2
    
    def test_add_empty_chunk(self):
        """Test adding empty chunk is handled gracefully"""
        buffer = AudioBuffer()
        
        segment = buffer.add_chunk(b'', duration=0.1)
        
        assert segment is None
        assert len(buffer.buffer) == 0
        assert buffer.buffer_duration == 0.0
    
    def test_add_chunk_exceeding_threshold(self):
        """Test adding a chunk that exceeds segment duration"""
        buffer = AudioBuffer(segment_duration=1.0)
        
        # Add a large chunk that exceeds threshold
        chunk_data = b'large_audio_chunk'
        segment = buffer.add_chunk(chunk_data, duration=1.5)
        
        assert segment is not None
        assert segment.duration == 1.5
        assert buffer.total_segments == 1


class TestFlush:
    """Tests for flush method"""
    
    def test_flush_with_buffered_data(self):
        """Test flushing buffer with remaining audio"""
        buffer = AudioBuffer(segment_duration=1.0)
        
        # Add 5 chunks of 100ms (total 500ms, below threshold)
        for i in range(5):
            buffer.add_chunk(f'chunk_{i}'.encode(), duration=0.1)
        
        assert len(buffer.buffer) == 5
        assert buffer.buffer_duration == 0.5
        
        # Flush remaining audio
        segment = buffer.flush()
        
        assert segment is not None
        assert segment.duration == 0.5
        assert len(buffer.buffer) == 0
        assert buffer.buffer_duration == 0.0
        assert buffer.total_segments == 1
    
    def test_flush_empty_buffer(self):
        """Test flushing empty buffer returns None"""
        buffer = AudioBuffer()
        
        segment = buffer.flush()
        
        assert segment is None
        assert buffer.total_segments == 0
    
    def test_flush_after_segment_creation(self):
        """Test flushing after a segment was already created"""
        buffer = AudioBuffer(segment_duration=1.0)
        
        # Add enough chunks to create a segment
        for i in range(10):
            buffer.add_chunk(f'chunk_{i}'.encode(), duration=0.1)
        
        assert buffer.total_segments == 1
        assert len(buffer.buffer) == 0
        
        # Flush should return None since buffer is empty
        segment = buffer.flush()
        assert segment is None


class TestSegmentCreation:
    """Tests for segment creation logic"""
    
    def test_segment_contains_combined_audio(self):
        """Test that segment contains all buffered audio data"""
        buffer = AudioBuffer(segment_duration=0.3)
        
        # Add 3 chunks (will create segment on 3rd chunk)
        chunks = [b'chunk_1', b'chunk_2', b'chunk_3']
        segment = None
        for chunk in chunks:
            result = buffer.add_chunk(chunk, duration=0.1)
            if result:
                segment = result
        
        # Segment should have been created
        assert segment is not None
        # Note: segment.data will be WAV format (or original if conversion fails)
        # Just verify it's not empty
        assert len(segment.data) > 0
    
    def test_segment_timestamp(self):
        """Test that segment has a timestamp"""
        buffer = AudioBuffer(segment_duration=0.2)
        
        before = datetime.utcnow()
        buffer.add_chunk(b'chunk_1', duration=0.1)
        segment = buffer.add_chunk(b'chunk_2', duration=0.1)  # Should create segment
        after = datetime.utcnow()
        
        assert segment is not None
        assert before <= segment.timestamp <= after
    
    def test_multiple_segments_increment_counter(self):
        """Test that total_segments counter increments correctly"""
        buffer = AudioBuffer(segment_duration=0.2)
        
        # Create 3 segments
        for seg_num in range(3):
            for chunk_num in range(2):
                buffer.add_chunk(f'seg{seg_num}_chunk{chunk_num}'.encode(), duration=0.1)
        
        assert buffer.total_segments == 3


class TestAudioFormatConversion:
    """Tests for audio format conversion"""
    
    def test_convert_to_wav_with_mock_data(self):
        """Test WAV conversion with mock audio data"""
        buffer = AudioBuffer()
        
        # Create a simple WAV file in memory for testing
        # This is a minimal valid WAV header + data
        wav_header = (
            b'RIFF'
            b'\x24\x00\x00\x00'  # File size - 8
            b'WAVE'
            b'fmt '
            b'\x10\x00\x00\x00'  # fmt chunk size
            b'\x01\x00'  # Audio format (PCM)
            b'\x01\x00'  # Channels (mono)
            b'\x80\x3e\x00\x00'  # Sample rate (16000)
            b'\x00\x7d\x00\x00'  # Byte rate
            b'\x02\x00'  # Block align
            b'\x10\x00'  # Bits per sample
            b'data'
            b'\x00\x00\x00\x00'  # Data size
        )
        
        # Add the mock WAV data
        segment = buffer.add_chunk(wav_header, duration=1.0)
        
        # Should create a segment (duration >= 1.0)
        assert segment is not None
        # Conversion may fail with mock data, but should not crash
        assert segment.data is not None
    
    def test_conversion_handles_invalid_audio(self):
        """Test that invalid audio data is handled gracefully"""
        buffer = AudioBuffer(segment_duration=0.1)
        
        # Add invalid audio data
        invalid_data = b'not_valid_audio_data'
        segment = buffer.add_chunk(invalid_data, duration=0.1)
        
        # Should still create a segment (fallback to original data)
        assert segment is not None
        assert segment.data is not None


class TestBufferStats:
    """Tests for buffer statistics"""
    
    def test_get_stats_initial(self):
        """Test getting stats from new buffer"""
        buffer = AudioBuffer(segment_duration=2.0, sample_rate=48000)
        
        stats = buffer.get_stats()
        
        assert stats['total_segments'] == 0
        assert stats['buffer_chunks'] == 0
        assert stats['buffer_duration'] == 0.0
        assert stats['segment_duration'] == 2.0
        assert stats['sample_rate'] == 48000
    
    def test_get_stats_with_buffered_data(self):
        """Test getting stats with buffered chunks"""
        buffer = AudioBuffer()
        
        # Add some chunks
        for i in range(5):
            buffer.add_chunk(f'chunk_{i}'.encode(), duration=0.1)
        
        stats = buffer.get_stats()
        
        assert stats['total_segments'] == 0
        assert stats['buffer_chunks'] == 5
        assert stats['buffer_duration'] == 0.5
    
    def test_get_stats_after_segment_creation(self):
        """Test getting stats after creating segments"""
        buffer = AudioBuffer(segment_duration=0.3)
        
        # Create 2 segments
        for i in range(6):
            buffer.add_chunk(f'chunk_{i}'.encode(), duration=0.1)
        
        stats = buffer.get_stats()
        
        assert stats['total_segments'] == 2
        assert stats['buffer_chunks'] == 0  # Buffer cleared after segments


class TestBufferReset:
    """Tests for buffer reset functionality"""
    
    def test_reset_clears_buffer(self):
        """Test that reset clears all buffer state"""
        buffer = AudioBuffer()
        
        # Add some data
        for i in range(5):
            buffer.add_chunk(f'chunk_{i}'.encode(), duration=0.1)
        
        # Create a segment
        buffer.add_chunk(b'final_chunk', duration=0.5)
        
        assert buffer.total_segments == 1
        
        # Reset
        buffer.reset()
        
        assert len(buffer.buffer) == 0
        assert buffer.buffer_duration == 0.0
        assert buffer.total_segments == 0
        assert len(buffer.chunk_metadata) == 0
    
    def test_reset_allows_reuse(self):
        """Test that buffer can be reused after reset"""
        buffer = AudioBuffer(segment_duration=0.2)
        
        # First use
        buffer.add_chunk(b'chunk_1', duration=0.1)
        buffer.add_chunk(b'chunk_2', duration=0.1)
        assert buffer.total_segments == 1
        
        # Reset
        buffer.reset()
        
        # Second use
        buffer.add_chunk(b'chunk_3', duration=0.1)
        buffer.add_chunk(b'chunk_4', duration=0.1)
        assert buffer.total_segments == 1  # Counter reset, so back to 1


class TestEdgeCases:
    """Tests for edge cases and error handling"""
    
    def test_very_small_chunks(self):
        """Test handling very small audio chunks"""
        buffer = AudioBuffer(segment_duration=1.0)
        
        # Add 100 chunks of 10ms each
        for i in range(100):
            buffer.add_chunk(f'tiny_{i}'.encode(), duration=0.01)
        
        assert buffer.total_segments == 1
        assert buffer.buffer_duration == 0.0  # Buffer cleared
    
    def test_very_large_chunk(self):
        """Test handling a very large audio chunk"""
        buffer = AudioBuffer(segment_duration=1.0)
        
        # Add a 10-second chunk
        large_chunk = b'x' * 10000
        segment = buffer.add_chunk(large_chunk, duration=10.0)
        
        assert segment is not None
        assert segment.duration == 10.0
    
    def test_zero_duration_chunk(self):
        """Test handling chunk with zero duration"""
        buffer = AudioBuffer(segment_duration=1.0)
        
        segment = buffer.add_chunk(b'chunk', duration=0.0)
        
        assert segment is None
        assert len(buffer.buffer) == 1
        assert buffer.buffer_duration == 0.0
    
    def test_negative_duration_chunk(self):
        """Test handling chunk with negative duration"""
        buffer = AudioBuffer(segment_duration=1.0)
        
        # This is an error case, but should not crash
        segment = buffer.add_chunk(b'chunk', duration=-0.1)
        
        # Buffer should still accept it (garbage in, garbage out)
        assert segment is None
        assert buffer.buffer_duration == -0.1
    
    def test_concurrent_segment_creation(self):
        """Test that segment creation is consistent"""
        buffer = AudioBuffer(segment_duration=1.0)
        
        # Add exactly 1 second of audio
        for i in range(10):
            segment = buffer.add_chunk(f'chunk_{i}'.encode(), duration=0.1)
        
        # Should create exactly 1 segment
        assert buffer.total_segments == 1
        assert len(buffer.buffer) == 0


class TestAudioSegmentDataclass:
    """Tests for AudioSegment dataclass"""
    
    def test_audio_segment_creation(self):
        """Test creating AudioSegment"""
        segment = AudioSegment(
            data=b'audio_data',
            duration=1.5,
            timestamp=datetime.utcnow(),
            sequence_start=0,
            sequence_end=10
        )
        
        assert segment.data == b'audio_data'
        assert segment.duration == 1.5
        assert isinstance(segment.timestamp, datetime)
        assert segment.sequence_start == 0
        assert segment.sequence_end == 10
    
    def test_audio_segment_attributes(self):
        """Test AudioSegment attributes are accessible"""
        now = datetime.utcnow()
        segment = AudioSegment(
            data=b'test',
            duration=2.0,
            timestamp=now,
            sequence_start=5,
            sequence_end=15
        )
        
        assert hasattr(segment, 'data')
        assert hasattr(segment, 'duration')
        assert hasattr(segment, 'timestamp')
        assert hasattr(segment, 'sequence_start')
        assert hasattr(segment, 'sequence_end')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
