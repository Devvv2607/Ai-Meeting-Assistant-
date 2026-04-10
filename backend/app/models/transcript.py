from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Transcript(Base):
    """Transcript model for storing transcription data"""

    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    speaker = Column(String(255), nullable=False)
    text = Column(String(5000), nullable=False)
    start_time = Column(Float, nullable=False)  # Start time in seconds
    end_time = Column(Float, nullable=False)    # End time in seconds
    embedding = Column(LargeBinary, nullable=True)  # Store embedding as binary
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    meeting = relationship("Meeting", back_populates="transcripts")

    def __repr__(self):
        return f"<Transcript(id={self.id}, meeting_id={self.meeting_id}, speaker={self.speaker})>"
