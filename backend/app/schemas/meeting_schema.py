from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MeetingStatusEnum(str, Enum):
    """Meeting status enum"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MeetingCreate(BaseModel):
    """Meeting creation schema"""

    title: str
    description: Optional[str] = None


class MeetingUpdate(BaseModel):
    """Meeting update schema"""

    title: Optional[str] = None
    description: Optional[str] = None


class MeetingResponse(BaseModel):
    """Meeting response schema"""

    id: int
    user_id: int
    title: str
    description: Optional[str]
    audio_url: str
    duration: Optional[float]
    status: MeetingStatusEnum
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MeetingListResponse(BaseModel):
    """Meeting list response schema"""

    id: int
    title: str
    status: MeetingStatusEnum
    duration: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True
