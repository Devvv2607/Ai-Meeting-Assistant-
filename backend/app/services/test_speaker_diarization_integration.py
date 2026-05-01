"""
Integration tests for SpeakerDiarizationService with AudioBuffer

Tests the integration between speaker diarization and audio buffer
for live meeting scenarios.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
from app.services.speaker_diarization import SpeakerDiarizationService
from app.services.audio_buffer import AudioBuffer


class TestSpeakerDiarizationIntegration:
    """Integration tests for speaker diarization with audio buffer"""
    
    @pytest.fixture
    def service(self):
        """Create a SpeakerDiarizationService instance"""
        service = SpeakerDiarizationService()
        # Mock the pipeline
        service.pipeline = Mock()
        service.embedding_model = Mock()
        return service
    
    @pytest.fixture
    def audio_buffer(self):
        """Create an AudioBuffer instance"""
        return AudioBuffer(segment_duration=1.0)
    
    @pytest.mark.asyncio
    async def test_live_meeting_scenario(self, service, audio_buffer):
        """Test a complete live meeting scenario with multiple speakers"""
        session_id = "live_meeting_001"
        
        # Simulate 3 speakers with distinct embeddings
        speaker_embeddings = {
            "Speaker A": np.array([1.0, 0.0, 0.0]),
            "Speaker B": np.array([0.0, 1.0, 0.0]),
            "Speaker C": np.array([0.0, 0.0, 1.0])
        }
        
        # Simulate a conversation with 10 turns
        conversation_turns = [
            "Speaker A", "Speaker B", "Speaker A", "Speaker C",
            "Speaker B", "Speaker A", "Speaker C", "Speaker B",
            "Speaker A", "Speaker C"
        ]
        
        detected_speakers = []
        
        for turn, actual_speaker in enumerate(conversation_turns, 1):
            # Get embedding for this speaker
            embedding = speaker_embeddings[actual_speaker]
            
            # Add small noise to simulate real-world variation
            noisy_embedding = embedding + np.random.normal(0, 0.03, embedding.shape)
            
            # Identify speaker
            speaker_id, confidence = service._match_speaker(noisy_embedding, session_id)
            detected_speakers.append(speaker_id)
            
            # Verify confidence is high for matched speakers
            if turn > 3:  # After first 3 turns, all speakers are known
                assert confidence >= service.similarity_threshold
        
        # Verify we detected exactly 3 unique speakers
        unique_speakers = set(detected_speakers)
        assert len(unique_speakers) == 3
        
        # Verify speaker consistency (same actual speaker → same detected speaker)
        speaker_mapping = {}
        for actual, detected in zip(conversation_turns, detected_speakers):
            if actual not in speaker_mapping:
                speaker_mapping[actual] = detected
            else:
                assert speaker_mapping[actual] == detected
        
        # Clean up
        service.clear_session(session_id)
    
    @pytest.mark.asyncio
    async def test_speaker_joins_mid_meeting(self, service):
        """Test detecting a new speaker joining mid-meeting"""
        session_id = "meeting_with_late_joiner"
        
        # Initial 2 speakers
        emb1 = np.array([1.0, 0.0, 0.0])
        emb2 = np.array([0.0, 1.0, 0.0])
        
        speaker1, _ = service._match_speaker(emb1, session_id)
        speaker2, _ = service._match_speaker(emb2, session_id)
        
        assert speaker1 == "Speaker 1"
        assert speaker2 == "Speaker 2"
        assert service.speaker_counters[session_id] == 2
        
        # Simulate several turns with existing speakers
        for _ in range(5):
            service._match_speaker(emb1 + np.random.normal(0, 0.02, 3), session_id)
            service._match_speaker(emb2 + np.random.normal(0, 0.02, 3), session_id)
        
        # Still only 2 speakers
        assert service.speaker_counters[session_id] == 2
        
        # New speaker joins
        emb3 = np.array([0.0, 0.0, 1.0])
        speaker3, confidence = service._match_speaker(emb3, session_id)
        
        assert speaker3 == "Speaker 3"
        assert confidence == 1.0  # High confidence for new speaker
        assert service.speaker_counters[session_id] == 3
        
        service.clear_session(session_id)
    
    @pytest.mark.asyncio
    async def test_speaker_leaves_and_returns(self, service):
        """Test speaker leaving and returning to meeting"""
        session_id = "meeting_with_break"
        
        # 3 speakers initially
        embeddings = [
            np.array([1.0, 0.0, 0.0]),
            np.array([0.0, 1.0, 0.0]),
            np.array([0.0, 0.0, 1.0])
        ]
        
        # All speakers speak once
        speaker_ids = []
        for emb in embeddings:
            speaker_id, _ = service._match_speaker(emb, session_id)
            speaker_ids.append(speaker_id)
        
        assert len(set(speaker_ids)) == 3
        
        # Speaker 2 leaves (only speakers 1 and 3 speak)
        for _ in range(5):
            service._match_speaker(embeddings[0] + np.random.normal(0, 0.02, 3), session_id)
            service._match_speaker(embeddings[2] + np.random.normal(0, 0.02, 3), session_id)
        
        # Speaker 2 returns
        returning_speaker, confidence = service._match_speaker(
            embeddings[1] + np.random.normal(0, 0.02, 3),
            session_id
        )
        
        # Should be recognized as the same speaker
        assert returning_speaker == speaker_ids[1]
        assert confidence > service.similarity_threshold
        
        # Still only 3 speakers total
        assert service.speaker_counters[session_id] == 3
        
        service.clear_session(session_id)
    
    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, service):
        """Test handling multiple concurrent sessions"""
        sessions = ["session_1", "session_2", "session_3"]
        
        # Create different speakers in each session
        for session_id in sessions:
            # Each session has exactly 3 speakers (fixed for deterministic test)
            num_speakers = 3
            
            for i in range(num_speakers):
                # Create distinct embeddings for each speaker
                embedding = np.zeros(5)
                embedding[i % 5] = 1.0
                embedding[(i + 1) % 5] = 0.1
                service._match_speaker(embedding, session_id)
        
        # Verify all sessions are tracked
        assert len(service.speaker_embeddings) == 3
        assert len(service.speaker_counters) == 3
        
        # Verify speaker counts
        for session_id in sessions:
            speakers = service.get_session_speakers(session_id)
            assert len(speakers) == 3
        
        # Clear one session
        service.clear_session(sessions[0])
        assert len(service.speaker_embeddings) == 2
        
        # Other sessions should be unaffected
        for session_id in sessions[1:]:
            speakers = service.get_session_speakers(session_id)
            assert len(speakers) == 3
        
        # Clean up
        for session_id in sessions[1:]:
            service.clear_session(session_id)
    
    @pytest.mark.asyncio
    async def test_speaker_similarity_edge_cases(self, service):
        """Test edge cases around similarity threshold"""
        session_id = "similarity_edge_cases"
        
        # Create first speaker
        base_embedding = np.array([1.0, 0.0, 0.0])
        speaker1, _ = service._match_speaker(base_embedding, session_id)
        
        # Test embeddings at different similarity levels
        test_cases = [
            (np.array([0.99, 0.14, 0.0]), "very_similar", True),   # ~0.99 similarity
            (np.array([0.85, 0.53, 0.0]), "similar", True),        # ~0.85 similarity
            (np.array([0.71, 0.71, 0.0]), "threshold", True),      # ~0.71 similarity (just above)
            (np.array([0.69, 0.72, 0.0]), "below_threshold", False), # ~0.69 similarity (just below)
            (np.array([0.0, 1.0, 0.0]), "orthogonal", False),      # 0.0 similarity
        ]
        
        for test_embedding, description, should_match in test_cases:
            speaker_id, confidence = service._match_speaker(test_embedding, session_id)
            
            if should_match:
                assert speaker_id == speaker1, f"Failed for {description}"
                assert confidence >= service.similarity_threshold
            else:
                assert speaker_id != speaker1, f"Failed for {description}"
        
        service.clear_session(session_id)
    
    @pytest.mark.asyncio
    async def test_memory_cleanup(self, service):
        """Test that session cleanup properly frees memory"""
        # Create multiple sessions with many speakers
        sessions = [f"session_{i}" for i in range(10)]
        
        for session_id in sessions:
            # Add 5 speakers per session
            for i in range(5):
                embedding = np.random.rand(100)  # Large embedding
                service._match_speaker(embedding, session_id)
        
        # Verify all sessions are tracked
        assert len(service.speaker_embeddings) == 10
        assert len(service.speaker_counters) == 10
        
        # Clear all sessions
        for session_id in sessions:
            service.clear_session(session_id)
        
        # Verify all data is cleared
        assert len(service.speaker_embeddings) == 0
        assert len(service.speaker_counters) == 0
    
    @pytest.mark.asyncio
    async def test_speaker_identification_with_audio_buffer(self, service, audio_buffer):
        """Test integration with AudioBuffer for segment processing"""
        session_id = "audio_buffer_integration"
        
        # Mock embedding extraction
        mock_embeddings = [
            np.array([1.0, 0.0, 0.0]),  # Speaker 1
            np.array([0.0, 1.0, 0.0]),  # Speaker 2
            np.array([1.0, 0.0, 0.0]),  # Speaker 1 again
        ]
        
        detected_speakers = []
        
        for i, embedding in enumerate(mock_embeddings):
            # Simulate audio segment from buffer
            audio_segment = b"fake_audio_segment_" + str(i).encode()
            
            # Mock the embedding extraction
            with patch.object(
                service,
                '_extract_embedding',
                new_callable=AsyncMock,
                return_value=embedding
            ):
                speaker_id, confidence = await service.identify_speaker(
                    audio_segment,
                    session_id
                )
                detected_speakers.append(speaker_id)
        
        # Verify speaker detection
        assert detected_speakers[0] == "Speaker 1"
        assert detected_speakers[1] == "Speaker 2"
        assert detected_speakers[2] == "Speaker 1"  # Same as first
        
        # Verify only 2 unique speakers
        assert service.speaker_counters[session_id] == 2
        
        service.clear_session(session_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
