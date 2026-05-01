"""Summary model for storing meeting summaries"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Summary(Base):
    """Model for storing meeting summaries and insights"""
    
    __tablename__ = "summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False, index=True)
    
    # Summary content
    summary_text = Column(Text, nullable=True)
    key_points = Column(JSON, nullable=True, default=[])
    action_items = Column(JSON, nullable=True, default=[])
    sentiment = Column(String(50), nullable=True, default="neutral")
    
    # Structured insights fields for live meeting intelligence
    decisions = Column(JSON, nullable=True)
    risks = Column(JSON, nullable=True)
    next_steps = Column(JSON, nullable=True)
    topics = Column(JSON, nullable=True)
    meeting_analytics = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    meeting = relationship("Meeting", back_populates="summary")
    
    def __repr__(self):
        return f"<Summary(id={self.id}, meeting_id={self.meeting_id})>"
