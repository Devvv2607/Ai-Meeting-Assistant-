from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, LargeBinary, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Transcript(Base):
    """Transcript model for storing transcription data"""

    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    speaker = Column(String(255), nullable=False)
    text = Column(Text, nullable=False)
    start_time = Column(Float, nullable=False)  # Start time in seconds
    end_time = Column(Float, nullable=False)    # End time in seconds
    embedding = Column(LargeBinary, nullable=True)  # Store embedding as binary
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Live meeting fields
    confidence = Column(Float, default=1.0)  # Transcription confidence score (0.0-1.0)
    language = Column(String(10), default='en')  # Detected language code
    is_final = Column(Boolean, default=True)  # Whether this is a final transcript or interim

    # Relationships
    meeting = relationship("Meeting", back_populates="transcripts")

    def __repr__(self):
        return f"<Transcript(id={self.id}, meeting_id={self.meeting_id}, speaker={self.speaker})>"
