from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Summary(Base):
    """Summary model for storing AI-generated summaries"""

    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), unique=True, nullable=False)
    summary = Column(String(5000), nullable=True)
    key_points = Column(JSON, nullable=True)  # List of key points
    action_items = Column(JSON, nullable=True)  # List of action items
    sentiment = Column(String(50), nullable=True)  # Overall sentiment
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    meeting = relationship("Meeting", back_populates="summary")

    def __repr__(self):
        return f"<Summary(id={self.id}, meeting_id={self.meeting_id})>"
