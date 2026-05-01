from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Speaker(Base):
    """Model for speakers in a meeting"""
    __tablename__ = "speakers"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False, index=True)
    speaker_number = Column(Integer, nullable=False)  # Speaker 1, Speaker 2, etc.
    speaker_name = Column(String(255), nullable=True)  # Optional custom name
    talk_time_seconds = Column(Float, default=0)
    word_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="speakers")
    
    def __repr__(self):
        return f"<Speaker {self.speaker_number} - Meeting {self.meeting_id}>"
