from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import User
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.summary import Summary
from app.schemas.transcript_schema import (
    TranscriptResponse,
    TranscriptFullResponse,
    SummaryResponse,
    SearchResponse,
    SearchResult,
)
from app.services.embedding_service import embedding_service
from app.routers.meeting_routes import get_current_user
import numpy as np
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/meetings", tags=["transcripts"])


@router.get("/{meeting_id}/transcript", response_model=TranscriptFullResponse)
async def get_transcript(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get meeting transcript

    Args:
        meeting_id: Meeting ID
        current_user: Current user
        db: Database session

    Returns:
        Full meeting transcript
    """
    meeting = (
        db.query(Meeting)
        .filter(Meeting.id == meeting_id, Meeting.user_id == current_user.id)
        .first()
    )

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    transcripts = (
        db.query(Transcript)
        .filter(Transcript.meeting_id == meeting_id)
        .order_by(Transcript.start_time)
        .all()
    )

    return {
        "meeting_id": meeting_id,
        "segments": transcripts,
        "total_duration": meeting.duration or 0,
    }


@router.get("/{meeting_id}/summary", response_model=SummaryResponse)
async def get_summary(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get meeting summary

    Args:
        meeting_id: Meeting ID
        current_user: Current user
        db: Database session

    Returns:
        Meeting summary
    """
    meeting = (
        db.query(Meeting)
        .filter(Meeting.id == meeting_id, Meeting.user_id == current_user.id)
        .first()
    )

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    summary = db.query(Summary).filter(Summary.meeting_id == meeting_id).first()

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary not available yet. Meeting is still processing.",
        )

    return summary


@router.get("/{meeting_id}/search", response_model=SearchResponse)
async def search_transcript(
    meeting_id: int,
    q: str = Query(..., min_length=1, max_length=500),
    top_k: int = Query(5, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search meeting transcript

    Args:
        meeting_id: Meeting ID
        q: Search query
        top_k: Number of top results to return
        current_user: Current user
        db: Database session

    Returns:
        Search results
    """
    meeting = (
        db.query(Meeting)
        .filter(Meeting.id == meeting_id, Meeting.user_id == current_user.id)
        .first()
    )

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    try:
        # Get all transcripts
        transcripts = (
            db.query(Transcript)
            .filter(Transcript.meeting_id == meeting_id)
            .all()
        )

        if not transcripts:
            return {
                "query": q,
                "results": [],
                "total_results": 0,
            }

        # Generate query embedding
        query_embedding = embedding_service.encode_single(q)

        # Load embeddings and calculate similarity
        similarities = []
        for transcript in transcripts:
            if transcript.embedding:
                try:
                    embedding = np.array(json.loads(transcript.embedding))
                    similarity = np.dot(query_embedding, embedding) / (
                        np.linalg.norm(query_embedding)
                        * np.linalg.norm(embedding)
                    )
                    similarities.append((transcript, float(similarity)))
                except Exception as e:
                    logger.error(f"Error calculating similarity: {e}")
                    continue

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Get top results
        results = []
        for transcript, similarity in similarities[:top_k]:
            results.append(
                SearchResult(
                    transcript_id=transcript.id,
                    speaker=transcript.speaker,
                    text=transcript.text,
                    start_time=transcript.start_time,
                    end_time=transcript.end_time,
                    relevance_score=similarity,
                )
            )

        logger.info(f"Search returned {len(results)} results for query: {q}")

        return {
            "query": q,
            "results": results,
            "total_results": len(results),
        }

    except Exception as e:
        logger.error(f"Error searching transcript: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error searching transcript",
        )
