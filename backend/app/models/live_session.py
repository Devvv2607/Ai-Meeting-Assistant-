from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class LiveSession(Base):
    """Model for live meeting sessions"""
    __tablename__ = "live_sessions"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False, index=True)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    status = Column(String(50), default="ACTIVE")  # ACTIVE, ENDED, FAILED
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, default=0)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="live_session")
    
    def __repr__(self):
        return f"<LiveSession {self.id} - Meeting {self.meeting_id} - {self.status}>"
