"""
Speaker Diarization Service for Live Meeting Intelligence

This service identifies and tracks speakers throughout a live meeting using
pyannote.audio for speaker diarization and embedding-based speaker matching.

Key Features:
- Speaker identification using pyannote.audio pipeline
- Speaker embedding extraction and comparison
- Cosine similarity matching (threshold 0.7)
- Session-based speaker tracking
- New speaker detection and assignment

Requirements: 8.1-8.6
"""

from typing import Dict, Optional, Tuple
import logging
import numpy as np
import tempfile
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class SpeakerDiarizationService:
    """Service for identifying and tracking speakers in live meetings"""
    
    def __init__(self):
        """Initialize speaker diarization service with pyannote.audio pipeline"""
        self.pipeline = None
        self.embedding_model = None
        
        # Session-based speaker embeddings storage
        # Format: {session_id: {speaker_id: embedding_array}}
        self.speaker_embeddings: Dict[str, Dict[str, np.ndarray]] = {}
        
        # Speaker counters per session
        # Format: {session_id: speaker_count}
        self.speaker_counters: Dict[str, int] = {}
        
        # Similarity threshold for speaker matching
        self.similarity_threshold = 0.7
        
        # Initialize pyannote pipeline
        self._init_pipeline()
    
    def _init_pipeline(self):
        """Initialize pyannote.audio pipeline for speaker diarization"""
        try:
            from pyannote.audio import Pipeline
            
            logger.info("Initializing pyannote.audio speaker diarization pipeline")
            
            # Load pre-trained speaker diarization pipeline
            # Model: pyannote/speaker-diarization-3.1
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=os.getenv("HUGGINGFACE_TOKEN")
            )
            
            logger.info("✓ Speaker diarization pipeline initialized successfully")
            
        except ImportError as e:
            logger.error(
                "pyannote.audio not installed. Install with: "
                "pip install pyannote.audio"
            )
            logger.error(f"Import error: {e}")
            self.pipeline = None
            
        except Exception as e:
            logger.error(f"Failed to initialize speaker diarization pipeline: {e}")
            logger.error(
                "Note: pyannote.audio requires a HuggingFace token. "
                "Set HUGGINGFACE_TOKEN environment variable."
            )
            self.pipeline = None
    
    async def identify_speaker(
        self,
        audio_segment: bytes,
        session_id: str
    ) -> Tuple[str, float]:
        """Identify speaker in audio segment
        
        This method extracts a speaker embedding from the audio segment and
        compares it with known speakers in the session. If a match is found
        (cosine similarity > 0.7), returns the existing speaker_id. Otherwise,
        creates a new speaker.
        
        Args:
            audio_segment: Raw audio bytes (1-second segment in WAV format)
            session_id: Unique session identifier for tracking speakers
            
        Returns:
            Tuple of (speaker_id, confidence):
                - speaker_id: "Speaker 1", "Speaker 2", etc.
                - confidence: Similarity score (0.0-1.0)
                
        Requirements:
            - 8.1: Assign unique speaker_ids
            - 8.2: Maintain same speaker_id throughout meeting
            - 8.4: Detect and assign new speaker_id for new speakers
        """
        if not self.pipeline:
            logger.warning("Speaker diarization pipeline not available, using fallback")
            return self._fallback_speaker_id(session_id), 0.5
        
        try:
            # Extract speaker embedding from audio segment
            embedding = await self._extract_embedding(audio_segment)
            
            if embedding is None:
                logger.warning("Failed to extract speaker embedding, using fallback")
                return self._fallback_speaker_id(session_id), 0.5
            
            # Match speaker with existing speakers in session
            speaker_id, confidence = self._match_speaker(embedding, session_id)
            
            logger.debug(
                f"Speaker identified: {speaker_id} "
                f"(confidence={confidence:.2f}, session={session_id})"
            )
            
            return speaker_id, confidence
            
        except Exception as e:
            logger.error(f"Error identifying speaker: {e}", exc_info=True)
            return self._fallback_speaker_id(session_id), 0.5
    
    async def _extract_embedding(self, audio_segment: bytes) -> Optional[np.ndarray]:
        """Extract speaker embedding from audio segment
        
        Uses pyannote.audio's embedding model to extract a speaker embedding
        vector from the audio segment. This embedding represents the speaker's
        voice characteristics and can be compared with other embeddings.
        
        Args:
            audio_segment: Raw audio bytes in WAV format
            
        Returns:
            Speaker embedding as numpy array, or None if extraction fails
            
        Requirement: 8.1 (Speaker embedding extraction)
        """
        temp_path = None
        try:
            # Save audio segment to temporary file
            temp_path = self._save_temp_segment(audio_segment)
            
            # Extract embedding using pyannote pipeline
            # The pipeline returns diarization results, we'll use the embedding model
            from pyannote.audio import Inference
            
            # Initialize embedding model if not already done
            if self.embedding_model is None:
                self.embedding_model = Inference(
                    "pyannote/embedding",
                    use_auth_token=os.getenv("HUGGINGFACE_TOKEN")
                )
            
            # Extract embedding
            embedding = self.embedding_model(temp_path)
            
            # Convert to numpy array if needed
            if not isinstance(embedding, np.ndarray):
                embedding = np.array(embedding)
            
            logger.debug(f"Extracted speaker embedding: shape={embedding.shape}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error extracting speaker embedding: {e}", exc_info=True)
            return None
            
        finally:
            # Clean up temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temp file: {cleanup_error}")
    
    def _match_speaker(
        self,
        embedding: np.ndarray,
        session_id: str
    ) -> Tuple[str, float]:
        """Match embedding to known speaker or create new speaker
        
        Compares the input embedding with all known speaker embeddings in the
        session using cosine similarity. If similarity exceeds threshold (0.7),
        returns the matching speaker_id. Otherwise, creates a new speaker.
        
        Args:
            embedding: Speaker embedding vector
            session_id: Session identifier
            
        Returns:
            Tuple of (speaker_id, confidence):
                - speaker_id: Matched or new speaker ID
                - confidence: Similarity score (0.0-1.0)
                
        Requirements:
            - 8.1: Unique speaker_ids
            - 8.2: Maintain same speaker_id
            - 8.4: Detect new speakers
        """
        # Initialize session storage if needed
        if session_id not in self.speaker_embeddings:
            self.speaker_embeddings[session_id] = {}
            self.speaker_counters[session_id] = 0
        
        # Compare with known speakers
        best_match_id = None
        best_similarity = 0.0
        
        for speaker_id, known_embedding in self.speaker_embeddings[session_id].items():
            similarity = self._cosine_similarity(embedding, known_embedding)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match_id = speaker_id
        
        # Check if best match exceeds threshold
        if best_match_id and best_similarity > self.similarity_threshold:
            logger.debug(
                f"Matched existing speaker: {best_match_id} "
                f"(similarity={best_similarity:.3f})"
            )
            return best_match_id, best_similarity
        
        # No match found - create new speaker
        self.speaker_counters[session_id] += 1
        new_speaker_id = f"Speaker {self.speaker_counters[session_id]}"
        
        # Store embedding for future matching
        self.speaker_embeddings[session_id][new_speaker_id] = embedding
        
        logger.info(
            f"New speaker detected: {new_speaker_id} "
            f"(session={session_id}, total_speakers={self.speaker_counters[session_id]})"
        )
        
        return new_speaker_id, 1.0  # High confidence for new speaker
    
    def _cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings
        
        Cosine similarity measures the cosine of the angle between two vectors,
        ranging from -1 (opposite) to 1 (identical). For speaker embeddings,
        higher similarity indicates the same speaker.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0.0-1.0)
            
        Requirement: 8.1 (Speaker matching with cosine similarity)
        """
        try:
            # Normalize embeddings
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Calculate cosine similarity
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            
            # Ensure result is in [0, 1] range
            similarity = max(0.0, min(1.0, float(similarity)))
            
            return similarity
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    def _save_temp_segment(self, audio_data: bytes) -> str:
        """Save audio segment to temporary file
        
        Args:
            audio_data: Raw audio bytes in WAV format
            
        Returns:
            Path to temporary file
        """
        try:
            # Create temp file with .wav extension
            temp_file = tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False,
                mode='wb'
            )
            
            # Write audio data
            temp_file.write(audio_data)
            temp_file.flush()
            temp_file.close()
            
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Error saving temp audio segment: {e}")
            raise
    
    def _fallback_speaker_id(self, session_id: str) -> str:
        """Get fallback speaker ID when diarization is unavailable
        
        Returns "Speaker 1" for all segments when speaker diarization
        pipeline is not available.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Default speaker ID
        """
        # Initialize session if needed
        if session_id not in self.speaker_counters:
            self.speaker_counters[session_id] = 1
        
        return "Speaker 1"
    
    def diarize_audio(
        self,
        audio_file_path: str,
        session_token: str
    ) -> Dict[int, Dict]:
        """Perform speaker diarization on complete audio file
        
        This method processes the full audio file and identifies different speakers
        throughout the recording. It returns speaker segments with timing information.
        
        Args:
            audio_file_path: Path to the audio file (WAV format)
            session_token: Session identifier for tracking
            
        Returns:
            Dictionary mapping speaker numbers to speaker data:
            {
                1: {"talk_time": 45.2, "segments": [...]},
                2: {"talk_time": 38.7, "segments": [...]}
            }
            
        Requirement: 8.1-8.6 (Speaker diarization and tracking)
        """
        if not self.pipeline:
            logger.warning(
                "Speaker diarization pipeline not available, using fallback "
                "(single speaker)"
            )
            return self._fallback_diarization(audio_file_path)
        
        try:
            logger.info(f"Running speaker diarization on: {audio_file_path}")
            
            # Run pyannote.audio pipeline
            diarization = self.pipeline(audio_file_path)
            
            # Process diarization results
            speaker_data = {}
            speaker_mapping = {}  # Map pyannote labels to our speaker numbers
            next_speaker_num = 1
            
            for turn, _, speaker_label in diarization.itertracks(yield_label=True):
                # Map pyannote speaker labels to sequential numbers
                if speaker_label not in speaker_mapping:
                    speaker_mapping[speaker_label] = next_speaker_num
                    next_speaker_num += 1
                
                speaker_num = speaker_mapping[speaker_label]
                
                # Initialize speaker data if needed
                if speaker_num not in speaker_data:
                    speaker_data[speaker_num] = {
                        "talk_time": 0.0,
                        "segments": []
                    }
                
                # Add segment
                segment_duration = turn.end - turn.start
                speaker_data[speaker_num]["talk_time"] += segment_duration
                speaker_data[speaker_num]["segments"].append({
                    "start": turn.start,
                    "end": turn.end,
                    "duration": segment_duration
                })
            
            logger.info(
                f"Speaker diarization complete: {len(speaker_data)} speakers detected"
            )
            
            return speaker_data
            
        except Exception as e:
            logger.error(
                f"Error during speaker diarization: {e}",
                exc_info=True
            )
            logger.warning("Falling back to single speaker")
            return self._fallback_diarization(audio_file_path)
    
    def _fallback_diarization(self, audio_file_path: str) -> Dict[int, Dict]:
        """Fallback diarization when pyannote is not available
        
        Returns a single speaker with estimated talk time based on file size.
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Dictionary with single speaker data
        """
        try:
            # Estimate duration from file size (rough approximation)
            file_size = os.path.getsize(audio_file_path)
            # Assume ~16KB per second for WAV files (rough estimate)
            estimated_duration = file_size / 16000
            
            return {
                1: {
                    "talk_time": estimated_duration,
                    "segments": [{
                        "start": 0.0,
                        "end": estimated_duration,
                        "duration": estimated_duration
                    }]
                }
            }
        except Exception as e:
            logger.error(f"Error in fallback diarization: {e}")
            # Return minimal fallback
            return {
                1: {
                    "talk_time": 0.0,
                    "segments": []
                }
            }
    
    def clear_session(self, session_id: str):
        """Clear speaker data for a session
        
        Removes all speaker embeddings and counters for the specified session.
        Should be called when a meeting ends to free memory.
        
        Args:
            session_id: Session identifier to clear
            
        Requirement: 8.5 (Session cleanup)
        """
        if session_id in self.speaker_embeddings:
            del self.speaker_embeddings[session_id]
            logger.info(f"Cleared speaker embeddings for session: {session_id}")
        
        if session_id in self.speaker_counters:
            del self.speaker_counters[session_id]
            logger.info(f"Cleared speaker counter for session: {session_id}")
    
    def cleanup_session(self, session_token: str):
        """Alias for clear_session to match the method name used in live_audio_processor
        
        Args:
            session_token: Session identifier to clear
        """
        self.clear_session(session_token)
    
    def get_session_speakers(self, session_id: str) -> Dict[str, int]:
        """Get all speakers detected in a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary mapping speaker_id to speaker_number
            Example: {"Speaker 1": 1, "Speaker 2": 2}
        """
        if session_id not in self.speaker_embeddings:
            return {}
        
        speakers = {}
        for speaker_id in self.speaker_embeddings[session_id].keys():
            # Extract speaker number from "Speaker N" format
            try:
                speaker_num = int(speaker_id.split()[-1])
                speakers[speaker_id] = speaker_num
            except (ValueError, IndexError):
                speakers[speaker_id] = 0
        
        return speakers
    
    def rename_speaker(
        self,
        meeting_id: int,
        old_speaker_id: str,
        new_speaker_name: str,
        db
    ) -> bool:
        """Rename a speaker and update all associated transcript segments
        
        This method updates both the Speaker model record and all Transcript
        records that reference the old speaker_id. The operation is performed
        within a database transaction to ensure consistency.
        
        Args:
            meeting_id: Meeting identifier
            old_speaker_id: Current speaker identifier (e.g., "Speaker 1")
            new_speaker_name: New name for the speaker (e.g., "Alice")
            db: Database session
            
        Returns:
            True if rename was successful, False otherwise
            
        Raises:
            ValueError: If speaker_id is invalid or not found
            
        Requirement: 8.7 (Speaker rename functionality)
        """
        try:
            from app.models.speaker import Speaker
            from app.models.transcript import Transcript
            
            # Extract speaker number from speaker_id (e.g., "Speaker 1" -> 1)
            try:
                speaker_number = int(old_speaker_id.split()[-1])
            except (ValueError, IndexError):
                logger.error(f"Invalid speaker_id format: {old_speaker_id}")
                raise ValueError(f"Invalid speaker_id format: {old_speaker_id}")
            
            # Find the Speaker record
            speaker = db.query(Speaker).filter(
                Speaker.meeting_id == meeting_id,
                Speaker.speaker_number == speaker_number
            ).first()
            
            if not speaker:
                logger.error(
                    f"Speaker not found: meeting_id={meeting_id}, "
                    f"speaker_number={speaker_number}"
                )
                raise ValueError(
                    f"Speaker {old_speaker_id} not found in meeting {meeting_id}"
                )
            
            # Update Speaker model with new name
            speaker.speaker_name = new_speaker_name
            
            # Update all Transcript records with the old speaker_id
            # The transcript.speaker field stores the speaker_id (e.g., "Speaker 1")
            # We need to update it to the new name
            transcripts_updated = db.query(Transcript).filter(
                Transcript.meeting_id == meeting_id,
                Transcript.speaker == old_speaker_id
            ).update(
                {Transcript.speaker: new_speaker_name},
                synchronize_session=False
            )
            
            # Commit the transaction
            db.commit()
            
            logger.info(
                f"Successfully renamed speaker: meeting_id={meeting_id}, "
                f"old_id={old_speaker_id}, new_name={new_speaker_name}, "
                f"transcripts_updated={transcripts_updated}"
            )
            
            return True
            
        except ValueError:
            # Re-raise ValueError for invalid input
            db.rollback()
            raise
            
        except Exception as e:
            # Rollback transaction on any error
            db.rollback()
            logger.error(
                f"Error renaming speaker: meeting_id={meeting_id}, "
                f"old_id={old_speaker_id}, new_name={new_speaker_name}, "
                f"error={e}",
                exc_info=True
            )
            return False


# Global speaker diarization service instance
speaker_diarization_service = SpeakerDiarizationService()
