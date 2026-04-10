from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class TranscriptSegment(BaseModel):
    """Single transcript segment"""

    speaker: str
    text: str
    start_time: float
    end_time: float


class TranscriptResponse(BaseModel):
    """Transcript response schema"""

    id: int
    meeting_id: int
    speaker: str
    text: str
    start_time: float
    end_time: float
    created_at: datetime

    class Config:
        from_attributes = True


class TranscriptFullResponse(BaseModel):
    """Full transcript response"""

    meeting_id: int
    segments: List[TranscriptResponse]
    total_duration: float


class SummaryResponse(BaseModel):
    """Summary response schema"""

    id: int
    meeting_id: int
    summary: Optional[str]
    key_points: Optional[List[str]]
    action_items: Optional[List[str]]
    sentiment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SearchResult(BaseModel):
    """Search result schema"""

    transcript_id: int
    speaker: str
    text: str
    start_time: float
    end_time: float
    relevance_score: float


class SearchResponse(BaseModel):
    """Search response schema"""

    query: str
    results: List[SearchResult]
    total_results: int
