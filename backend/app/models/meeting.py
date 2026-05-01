from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import enum


class MeetingStatus(str, enum.Enum):
    """Meeting processing status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Meeting(Base):
    """Meeting model for storing meeting metadata"""

    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    audio_url = Column(String(500), nullable=False)
    duration = Column(Float, nullable=True)  # Duration in seconds
    status = Column(String(20), default=MeetingStatus.PENDING.value)  # Use String instead of Enum
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    celery_task_id = Column(String(255), nullable=True)

    # Relationships
    user = relationship("User", back_populates="meetings")
    transcripts = relationship("Transcript", back_populates="meeting", cascade="all, delete-orphan")
    summary = relationship("Summary", back_populates="meeting", uselist=False, cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="meeting", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="meeting", cascade="all, delete-orphan")
    speakers = relationship("Speaker", back_populates="meeting", cascade="all, delete-orphan")
    live_session = relationship("LiveSession", back_populates="meeting", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Meeting(id={self.id}, title={self.title}, status={self.status})>"
