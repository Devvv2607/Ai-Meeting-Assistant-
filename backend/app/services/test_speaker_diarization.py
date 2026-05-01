"""
Unit tests for SpeakerDiarizationService

Tests speaker identification, embedding extraction, speaker matching,
and session management functionality.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
from app.services.speaker_diarization import SpeakerDiarizationService


class TestSpeakerDiarizationService:
    """Test suite for SpeakerDiarizationService"""
    
    @pytest.fixture
    def service(self):
        """Create a SpeakerDiarizationService instance for testing"""
        service = SpeakerDiarizationService()
        # Mock the pipeline to avoid requiring HuggingFace token
        service.pipeline = Mock()
        service.embedding_model = Mock()
        return service
    
    @pytest.fixture
    def sample_audio_segment(self):
        """Create a sample audio segment (mock WAV data)"""
        # Create 1 second of silence at 16kHz sample rate
        sample_rate = 16000
        duration = 1.0
        samples = int(sample_rate * duration)
        
        # WAV header + audio data
        import struct
        import io
        
        wav_buffer = io.BytesIO()
        
        # Write WAV header
        wav_buffer.write(b'RIFF')
        wav_buffer.write(struct.pack('<I', 36 + samples * 2))
        wav_buffer.write(b'WAVE')
        wav_buffer.write(b'fmt ')
        wav_buffer.write(struct.pack('<I', 16))  # fmt chunk size
        wav_buffer.write(struct.pack('<H', 1))   # PCM format
        wav_buffer.write(struct.pack('<H', 1))   # mono
        wav_buffer.write(struct.pack('<I', sample_rate))
        wav_buffer.write(struct.pack('<I', sample_rate * 2))  # byte rate
        wav_buffer.write(struct.pack('<H', 2))   # block align
        wav_buffer.write(struct.pack('<H', 16))  # bits per sample
        wav_buffer.write(b'data')
        wav_buffer.write(struct.pack('<I', samples * 2))
        
        # Write audio data (silence)
        for _ in range(samples):
            wav_buffer.write(struct.pack('<h', 0))
        
        return wav_buffer.getvalue()
    
    def test_initialization(self, service):
        """Test service initialization"""
        assert service.similarity_threshold == 0.7
        assert isinstance(service.speaker_embeddings, dict)
        assert isinstance(service.speaker_counters, dict)
        assert len(service.speaker_embeddings) == 0
        assert len(service.speaker_counters) == 0
    
    def test_cosine_similarity_identical_vectors(self, service):
        """Test cosine similarity with identical vectors"""
        embedding = np.array([1.0, 2.0, 3.0])
        similarity = service._cosine_similarity(embedding, embedding)
        assert similarity == pytest.approx(1.0, abs=0.01)
    
    def test_cosine_similarity_orthogonal_vectors(self, service):
        """Test cosine similarity with orthogonal vectors"""
        embedding1 = np.array([1.0, 0.0, 0.0])
        embedding2 = np.array([0.0, 1.0, 0.0])
        similarity = service._cosine_similarity(embedding1, embedding2)
        assert similarity == pytest.approx(0.0, abs=0.01)
    
    def test_cosine_similarity_opposite_vectors(self, service):
        """Test cosine similarity with opposite vectors"""
        embedding1 = np.array([1.0, 2.0, 3.0])
        embedding2 = np.array([-1.0, -2.0, -3.0])
        similarity = service._cosine_similarity(embedding1, embedding2)
        # Cosine similarity is clamped to [0, 1], so -1 becomes 0
        assert similarity == pytest.approx(0.0, abs=0.01)
    
    def test_cosine_similarity_zero_vector(self, service):
        """Test cosine similarity with zero vector"""
        embedding1 = np.array([1.0, 2.0, 3.0])
        embedding2 = np.array([0.0, 0.0, 0.0])
        similarity = service._cosine_similarity(embedding1, embedding2)
        assert similarity == 0.0
    
    def test_match_speaker_new_session(self, service):
        """Test speaker matching in a new session"""
        session_id = "test_session_1"
        embedding = np.array([1.0, 2.0, 3.0])
        
        speaker_id, confidence = service._match_speaker(embedding, session_id)
        
        assert speaker_id == "Speaker 1"
        assert confidence == 1.0
        assert session_id in service.speaker_embeddings
        assert session_id in service.speaker_counters
        assert service.speaker_counters[session_id] == 1
    
    def test_match_speaker_existing_speaker(self, service):
        """Test matching an existing speaker"""
        session_id = "test_session_2"
        embedding1 = np.array([1.0, 2.0, 3.0])
        
        # First appearance - create new speaker
        speaker_id1, conf1 = service._match_speaker(embedding1, session_id)
        assert speaker_id1 == "Speaker 1"
        
        # Second appearance - should match existing speaker
        embedding2 = np.array([1.01, 2.01, 3.01])  # Very similar
        speaker_id2, conf2 = service._match_speaker(embedding2, session_id)
        
        assert speaker_id2 == "Speaker 1"
        assert conf2 > service.similarity_threshold
        assert service.speaker_counters[session_id] == 1  # No new speaker
    
    def test_match_speaker_new_speaker(self, service):
        """Test detecting a new speaker"""
        session_id = "test_session_3"
        
        # First speaker
        embedding1 = np.array([1.0, 0.0, 0.0])
        speaker_id1, _ = service._match_speaker(embedding1, session_id)
        assert speaker_id1 == "Speaker 1"
        
        # Second speaker (very different embedding)
        embedding2 = np.array([0.0, 1.0, 0.0])
        speaker_id2, _ = service._match_speaker(embedding2, session_id)
        assert speaker_id2 == "Speaker 2"
        assert service.speaker_counters[session_id] == 2
    
    def test_match_speaker_multiple_speakers(self, service):
        """Test matching with multiple speakers in session"""
        session_id = "test_session_4"
        
        # Create 3 different speakers
        embeddings = [
            np.array([1.0, 0.0, 0.0]),
            np.array([0.0, 1.0, 0.0]),
            np.array([0.0, 0.0, 1.0])
        ]
        
        speaker_ids = []
        for embedding in embeddings:
            speaker_id, _ = service._match_speaker(embedding, session_id)
            speaker_ids.append(speaker_id)
        
        assert speaker_ids == ["Speaker 1", "Speaker 2", "Speaker 3"]
        assert service.speaker_counters[session_id] == 3
        
        # Match with first speaker again
        similar_to_first = np.array([0.99, 0.01, 0.01])
        speaker_id, _ = service._match_speaker(similar_to_first, session_id)
        assert speaker_id == "Speaker 1"
        assert service.speaker_counters[session_id] == 3  # No new speaker
    
    def test_clear_session(self, service):
        """Test clearing session data"""
        session_id = "test_session_5"
        
        # Create some speakers
        embedding = np.array([1.0, 2.0, 3.0])
        service._match_speaker(embedding, session_id)
        
        assert session_id in service.speaker_embeddings
        assert session_id in service.speaker_counters
        
        # Clear session
        service.clear_session(session_id)
        
        assert session_id not in service.speaker_embeddings
        assert session_id not in service.speaker_counters
    
    def test_clear_nonexistent_session(self, service):
        """Test clearing a session that doesn't exist"""
        # Should not raise an error
        service.clear_session("nonexistent_session")
    
    def test_get_session_speakers_empty(self, service):
        """Test getting speakers from empty session"""
        speakers = service.get_session_speakers("nonexistent_session")
        assert speakers == {}
    
    def test_get_session_speakers(self, service):
        """Test getting speakers from session"""
        session_id = "test_session_6"
        
        # Create 2 speakers
        embedding1 = np.array([1.0, 0.0, 0.0])
        embedding2 = np.array([0.0, 1.0, 0.0])
        
        service._match_speaker(embedding1, session_id)
        service._match_speaker(embedding2, session_id)
        
        speakers = service.get_session_speakers(session_id)
        
        assert len(speakers) == 2
        assert speakers["Speaker 1"] == 1
        assert speakers["Speaker 2"] == 2
    
    def test_fallback_speaker_id(self, service):
        """Test fallback speaker ID generation"""
        session_id = "test_session_7"
        
        speaker_id = service._fallback_speaker_id(session_id)
        
        assert speaker_id == "Speaker 1"
        assert session_id in service.speaker_counters
        assert service.speaker_counters[session_id] == 1
    
    @pytest.mark.asyncio
    async def test_identify_speaker_without_pipeline(self, service):
        """Test speaker identification when pipeline is not available"""
        service.pipeline = None
        session_id = "test_session_8"
        audio_segment = b"fake_audio_data"
        
        speaker_id, confidence = await service.identify_speaker(
            audio_segment,
            session_id
        )
        
        assert speaker_id == "Speaker 1"
        assert confidence == 0.5
    
    @pytest.mark.asyncio
    async def test_identify_speaker_with_pipeline(self, service, sample_audio_segment):
        """Test speaker identification with pipeline"""
        session_id = "test_session_9"
        
        # Mock embedding extraction
        mock_embedding = np.array([1.0, 2.0, 3.0])
        
        with patch.object(
            service,
            '_extract_embedding',
            new_callable=AsyncMock,
            return_value=mock_embedding
        ):
            speaker_id, confidence = await service.identify_speaker(
                sample_audio_segment,
                session_id
            )
            
            assert speaker_id == "Speaker 1"
            assert confidence == 1.0
    
    @pytest.mark.asyncio
    async def test_identify_speaker_extraction_failure(self, service, sample_audio_segment):
        """Test speaker identification when embedding extraction fails"""
        session_id = "test_session_10"
        
        # Mock embedding extraction to return None
        with patch.object(
            service,
            '_extract_embedding',
            new_callable=AsyncMock,
            return_value=None
        ):
            speaker_id, confidence = await service.identify_speaker(
                sample_audio_segment,
                session_id
            )
            
            assert speaker_id == "Speaker 1"
            assert confidence == 0.5
    
    def test_save_temp_segment(self, service, sample_audio_segment):
        """Test saving audio segment to temp file"""
        import os
        
        temp_path = service._save_temp_segment(sample_audio_segment)
        
        try:
            assert os.path.exists(temp_path)
            assert temp_path.endswith('.wav')
            
            # Verify file content
            with open(temp_path, 'rb') as f:
                content = f.read()
                assert content == sample_audio_segment
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_similarity_threshold(self, service):
        """Test that similarity threshold is correctly set"""
        assert service.similarity_threshold == 0.7
        
        # Test that speakers below threshold are not matched
        session_id = "test_session_11"
        
        # Create first speaker
        embedding1 = np.array([1.0, 0.0, 0.0])
        speaker_id1, _ = service._match_speaker(embedding1, session_id)
        
        # Create embedding with similarity just below threshold
        # For orthogonal vectors, similarity is 0.0 (below 0.7)
        embedding2 = np.array([0.0, 1.0, 0.0])
        speaker_id2, _ = service._match_speaker(embedding2, session_id)
        
        # Should create new speaker
        assert speaker_id1 != speaker_id2
        assert speaker_id2 == "Speaker 2"


    def test_rename_speaker_success(self, service):
        """Test successful speaker rename"""
        from unittest.mock import MagicMock
        from app.models.speaker import Speaker
        from app.models.transcript import Transcript
        
        # Mock database session
        db = MagicMock()
        
        # Mock Speaker query
        mock_speaker = Speaker(
            id=1,
            meeting_id=100,
            speaker_number=1,
            speaker_name=None
        )
        db.query.return_value.filter.return_value.first.return_value = mock_speaker
        
        # Mock Transcript update
        db.query.return_value.filter.return_value.update.return_value = 5
        
        # Call rename_speaker
        result = service.rename_speaker(
            meeting_id=100,
            old_speaker_id="Speaker 1",
            new_speaker_name="Alice",
            db=db
        )
        
        assert result is True
        assert mock_speaker.speaker_name == "Alice"
        db.commit.assert_called_once()
    
    def test_rename_speaker_invalid_format(self, service):
        """Test rename with invalid speaker_id format"""
        from unittest.mock import MagicMock
        
        db = MagicMock()
        
        with pytest.raises(ValueError, match="Invalid speaker_id format"):
            service.rename_speaker(
                meeting_id=100,
                old_speaker_id="InvalidFormat",
                new_speaker_name="Alice",
                db=db
            )
        
        db.rollback.assert_called_once()
    
    def test_rename_speaker_not_found(self, service):
        """Test rename when speaker doesn't exist"""
        from unittest.mock import MagicMock
        
        db = MagicMock()
        
        # Mock Speaker query to return None
        db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(ValueError, match="Speaker .* not found"):
            service.rename_speaker(
                meeting_id=100,
                old_speaker_id="Speaker 1",
                new_speaker_name="Alice",
                db=db
            )
        
        db.rollback.assert_called_once()
    
    def test_rename_speaker_database_error(self, service):
        """Test rename with database error"""
        from unittest.mock import MagicMock
        from app.models.speaker import Speaker
        
        db = MagicMock()
        
        # Mock Speaker query
        mock_speaker = Speaker(
            id=1,
            meeting_id=100,
            speaker_number=1,
            speaker_name=None
        )
        db.query.return_value.filter.return_value.first.return_value = mock_speaker
        
        # Mock Transcript update to raise exception
        db.query.return_value.filter.return_value.update.side_effect = Exception("Database error")
        
        result = service.rename_speaker(
            meeting_id=100,
            old_speaker_id="Speaker 1",
            new_speaker_name="Alice",
            db=db
        )
        
        assert result is False
        db.rollback.assert_called_once()
    
    def test_rename_speaker_multiple_transcripts(self, service):
        """Test rename updates multiple transcript records"""
        from unittest.mock import MagicMock
        from app.models.speaker import Speaker
        
        db = MagicMock()
        
        # Mock Speaker query
        mock_speaker = Speaker(
            id=1,
            meeting_id=100,
            speaker_number=2,
            speaker_name=None
        )
        db.query.return_value.filter.return_value.first.return_value = mock_speaker
        
        # Mock Transcript update - 10 records updated
        db.query.return_value.filter.return_value.update.return_value = 10
        
        result = service.rename_speaker(
            meeting_id=100,
            old_speaker_id="Speaker 2",
            new_speaker_name="Bob",
            db=db
        )
        
        assert result is True
        assert mock_speaker.speaker_name == "Bob"
        db.commit.assert_called_once()
    
    def test_rename_speaker_with_existing_name(self, service):
        """Test renaming a speaker that already has a custom name"""
        from unittest.mock import MagicMock
        from app.models.speaker import Speaker
        
        db = MagicMock()
        
        # Mock Speaker with existing name
        mock_speaker = Speaker(
            id=1,
            meeting_id=100,
            speaker_number=1,
            speaker_name="OldName"
        )
        db.query.return_value.filter.return_value.first.return_value = mock_speaker
        
        # Mock Transcript update
        db.query.return_value.filter.return_value.update.return_value = 3
        
        result = service.rename_speaker(
            meeting_id=100,
            old_speaker_id="Speaker 1",
            new_speaker_name="NewName",
            db=db
        )
        
        assert result is True
        assert mock_speaker.speaker_name == "NewName"
        db.commit.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
