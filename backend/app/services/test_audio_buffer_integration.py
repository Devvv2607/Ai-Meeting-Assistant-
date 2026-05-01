"""Integration tests for AudioBuffer with realistic usage scenarios.

This module tests the AudioBuffer in scenarios that simulate real-world
usage in the live meeting system.
"""

import pytest
from datetime import datetime
from backend.app.services.audio_buffer import AudioBuffer, AudioSegment


class TestRealisticUsageScenarios:
    """Tests simulating real-world usage patterns"""
    
    def test_typical_live_meeting_flow(self):
        """Test a typical live meeting audio streaming flow"""
        buffer = AudioBuffer(segment_duration=1.0, sample_rate=16000)
        
        # Simulate 5 seconds of audio streaming (50 chunks of 100ms)
        segments_created = []
        for i in range(50):
            metadata = {
                'sequence_number': i,
                'timestamp': datetime.utcnow().timestamp()
            }
            segment = buffer.add_chunk(
                f'audio_chunk_{i}'.encode(),
                duration=0.1,
                metadata=metadata
            )
            if segment:
                segments_created.append(segment)
        
        # Should have created 5 segments (5 seconds / 1 second per segment)
        assert len(segments_created) == 5
        assert buffer.total_segments == 5
        
        # Each segment should have proper metadata
        for i, segment in enumerate(segments_created):
            assert segment.duration == pytest.approx(1.0, abs=0.01)
            assert isinstance(segment.timestamp, datetime)
            assert segment.sequence_start == i * 10
            assert segment.sequence_end == (i * 10) + 9
    
    def test_meeting_with_pause_and_resume(self):
        """Test pausing and resuming audio capture"""
        buffer = AudioBuffer(segment_duration=1.0)
        
        # Stream 1.5 seconds of audio
        for i in range(15):
            buffer.add_chunk(f'chunk_{i}'.encode(), duration=0.1)
        
        assert buffer.total_segments == 1
        
        # Pause (flush remaining audio)
        remaining = buffer.flush()
        assert remaining is not None
        assert remaining.duration == pytest.approx(0.5, abs=0.01)
        assert buffer.total_segments == 2
        
        # Resume (reset buffer for new session)
        buffer.reset()
        
        # Stream another 1 second
        for i in range(10):
            buffer.add_chunk(f'chunk_resume_{i}'.encode(), duration=0.1)
        
        assert buffer.total_segments == 1  # Counter reset
    
    def test_meeting_end_with_partial_segment(self):
        """Test ending a meeting with partial audio in buffer"""
        buffer = AudioBuffer(segment_duration=1.0)
        
        # Stream 2.3 seconds of audio
        for i in range(23):
            buffer.add_chunk(f'chunk_{i}'.encode(), duration=0.1)
        
        # Should have created 2 complete segments
        assert buffer.total_segments == 2
        
        # Buffer should have 0.3 seconds remaining
        assert buffer.buffer_duration == pytest.approx(0.3, abs=0.01)
        
        # Flush remaining audio when meeting ends
        final_segment = buffer.flush()
        assert final_segment is not None
        assert final_segment.duration == pytest.approx(0.3, abs=0.01)
        assert buffer.total_segments == 3
    
    def test_long_running_meeting(self):
        """Test a long-running meeting (simulating 1 minute)"""
        buffer = AudioBuffer(segment_duration=1.0)
        
        # Simulate 1 minute of audio (600 chunks of 100ms)
        segment_count = 0
        for i in range(600):
            segment = buffer.add_chunk(
                f'chunk_{i}'.encode(),
                duration=0.1
            )
            if segment:
                segment_count += 1
        
        # Should have created 60 segments (60 seconds)
        assert segment_count == 60
        assert buffer.total_segments == 60
        
        # Buffer should be empty (no partial segment)
        assert len(buffer.buffer) == 0
        assert buffer.buffer_duration == 0.0
    
    def test_variable_chunk_sizes(self):
        """Test handling variable chunk sizes (network jitter simulation)"""
        buffer = AudioBuffer(segment_duration=1.0)
        
        # Simulate variable chunk sizes due to network conditions
        chunk_durations = [0.08, 0.12, 0.09, 0.11, 0.10, 0.15, 0.05, 0.10, 0.10, 0.10]
        # Total: 1.0 seconds
        
        segment = None
        for i, duration in enumerate(chunk_durations):
            result = buffer.add_chunk(f'chunk_{i}'.encode(), duration)
            if result:
                segment = result
        
        # Should create exactly 1 segment
        assert segment is not None
        assert buffer.total_segments == 1
        assert segment.duration == pytest.approx(1.0, abs=0.01)
    
    def test_buffer_stats_during_streaming(self):
        """Test buffer statistics during active streaming"""
        buffer = AudioBuffer(segment_duration=1.0)
        
        # Add 5 chunks (0.5 seconds)
        for i in range(5):
            buffer.add_chunk(f'chunk_{i}'.encode(), duration=0.1)
        
        stats = buffer.get_stats()
        assert stats['total_segments'] == 0
        assert stats['buffer_chunks'] == 5
        assert stats['buffer_duration'] == pytest.approx(0.5, abs=0.01)
        
        # Add 5 more chunks (total 1.0 seconds, creates segment)
        for i in range(5, 10):
            buffer.add_chunk(f'chunk_{i}'.encode(), duration=0.1)
        
        stats = buffer.get_stats()
        assert stats['total_segments'] == 1
        assert stats['buffer_chunks'] == 0  # Buffer cleared after segment
        assert stats['buffer_duration'] == 0.0
    
    def test_metadata_tracking_across_segments(self):
        """Test that metadata is properly tracked across multiple segments"""
        buffer = AudioBuffer(segment_duration=0.5)
        
        segments = []
        for i in range(15):  # 1.5 seconds of audio
            metadata = {
                'sequence_number': i,
                'timestamp': 1000 + i * 100,
                'user_id': 123
            }
            segment = buffer.add_chunk(
                f'chunk_{i}'.encode(),
                duration=0.1,
                metadata=metadata
            )
            if segment:
                segments.append(segment)
        
        # Should create 3 segments
        assert len(segments) == 3
        
        # Check sequence ranges
        assert segments[0].sequence_start == 0
        assert segments[0].sequence_end == 4
        assert segments[1].sequence_start == 5
        assert segments[1].sequence_end == 9
        assert segments[2].sequence_start == 10
        assert segments[2].sequence_end == 14


class TestErrorRecovery:
    """Tests for error handling and recovery"""
    
    def test_recovery_after_conversion_failure(self):
        """Test that buffer continues working after audio conversion fails"""
        buffer = AudioBuffer(segment_duration=0.2)
        
        # Add chunks with invalid audio data (conversion will fail)
        segment = None
        for i in range(2):
            result = buffer.add_chunk(b'invalid_audio', duration=0.1)
            if result:
                segment = result
        
        # Should still create a segment (with original data as fallback)
        assert segment is not None
        assert segment.data is not None
        assert len(segment.data) > 0
        
        # Buffer should continue working
        for i in range(2):
            buffer.add_chunk(b'more_invalid', duration=0.1)
        
        assert buffer.total_segments == 2
    
    def test_buffer_state_after_error(self):
        """Test that buffer state is consistent after errors"""
        buffer = AudioBuffer(segment_duration=1.0)
        
        # Add some valid chunks
        for i in range(5):
            buffer.add_chunk(f'chunk_{i}'.encode(), duration=0.1)
        
        # Even if conversion fails, buffer should be cleared
        for i in range(5):
            buffer.add_chunk(b'invalid', duration=0.1)
        
        # Buffer should be empty after segment creation
        assert len(buffer.buffer) == 0
        assert buffer.buffer_duration == 0.0


class TestPerformance:
    """Tests for performance characteristics"""
    
    def test_memory_efficiency_with_many_segments(self):
        """Test that buffer doesn't accumulate memory with many segments"""
        buffer = AudioBuffer(segment_duration=0.1)
        
        # Create 100 segments
        for i in range(100):
            buffer.add_chunk(f'chunk_{i}'.encode(), duration=0.1)
        
        # Buffer should be empty (not accumulating data)
        assert len(buffer.buffer) == 0
        assert buffer.buffer_duration == 0.0
        
        # Only counter should increase
        assert buffer.total_segments == 100
    
    def test_buffer_capacity_limit(self):
        """Test buffer behavior with many small chunks"""
        buffer = AudioBuffer(segment_duration=1.0)
        
        # Add 1000 tiny chunks (0.001s each = 1 second total)
        # Note: Due to floating point precision, may not reach exactly 1.0
        for i in range(1000):
            buffer.add_chunk(f'tiny_{i}'.encode(), duration=0.001)
        
        # Should create exactly 1 segment (or be very close)
        assert buffer.total_segments >= 1
        # Buffer should be nearly empty
        assert buffer.buffer_duration < 0.01  # Less than 10ms remaining


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
