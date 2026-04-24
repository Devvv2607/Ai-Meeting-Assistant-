"""Document model for meeting context"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Document(Base):
    """Document model for storing uploaded documents"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf, docx, txt
    content = Column(Text, nullable=False)  # Extracted text content
    file_size = Column(Integer, nullable=False)  # Size in bytes
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    meeting = relationship("Meeting", back_populates="documents")
    user = relationship("User", back_populates="documents")
