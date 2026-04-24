"""Routes for meeting Q&A chatbot"""

from fastapi import APIRouter, Depends, HTTPException, status, Header, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.chat_message import ChatMessage, MessageRole
from app.models.document import Document
from app.utils.auth_utils import verify_token
from app.services.chatbot_service import chatbot_service
from app.services.document_service import document_service
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chatbot"])


def get_current_user(
    authorization: str = Header(...), db: Session = Depends(get_db)
) -> User:
    """Get current user from JWT token"""
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid scheme")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


@router.post("/meetings/{meeting_id}/chat")
async def ask_question(
    meeting_id: int,
    request_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ask a question about the meeting

    Args:
        meeting_id: Meeting ID
        request_data: {"question": "What was discussed?"}
        current_user: Current user
        db: Database session

    Returns:
        Answer with sources
    """
    try:
        # Verify meeting belongs to user
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

        # Get question
        question = request_data.get("question", "").strip()
        if not question:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question cannot be empty",
            )

        # Get transcripts
        transcripts = (
            db.query(Transcript)
            .filter(Transcript.meeting_id == meeting_id)
            .order_by(Transcript.start_time)
            .all()
        )

        if not transcripts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No transcripts available for this meeting",
            )

        # Get documents
        documents = (
            db.query(Document)
            .filter(Document.meeting_id == meeting_id)
            .all()
        )

        logger.info(f"Answering question for meeting {meeting_id}")

        # Get answer from chatbot
        result = chatbot_service.answer_question(
            question,
            transcripts,
            documents if documents else None
        )

        # Save user message
        user_message = ChatMessage(
            meeting_id=meeting_id,
            user_id=current_user.id,
            role=MessageRole.USER,
            content=question,
        )
        db.add(user_message)
        db.commit()

        # Save assistant message
        assistant_message = ChatMessage(
            meeting_id=meeting_id,
            user_id=current_user.id,
            role=MessageRole.ASSISTANT,
            content=result["answer"],
            sources=json.dumps(result["sources"]),
        )
        db.add(assistant_message)
        db.commit()

        logger.info(f"✓ Chat messages saved for meeting {meeting_id}")

        return {
            "answer": result["answer"],
            "sources": result["sources"],
            "context_used": result["context_used"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error answering question: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error answering question: {str(e)}",
        )


@router.get("/meetings/{meeting_id}/chat/history")
async def get_chat_history(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get chat history for a meeting

    Args:
        meeting_id: Meeting ID
        current_user: Current user
        db: Database session

    Returns:
        List of chat messages
    """
    try:
        # Verify meeting belongs to user
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

        # Get chat history
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.meeting_id == meeting_id)
            .order_by(ChatMessage.created_at)
            .all()
        )

        return {
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role.value,
                    "content": msg.content,
                    "sources": json.loads(msg.sources) if msg.sources else [],
                    "created_at": msg.created_at.isoformat(),
                }
                for msg in messages
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching chat history: {str(e)}",
        )


@router.post("/meetings/{meeting_id}/documents")
async def upload_document(
    meeting_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a document for the meeting

    Args:
        meeting_id: Meeting ID
        file: Document file
        current_user: Current user
        db: Database session

    Returns:
        Document metadata
    """
    try:
        # Verify meeting belongs to user
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

        # Read file content
        content = await file.read()

        logger.info(f"Processing document upload: {file.filename}")

        # Process document
        doc_data = document_service.process_document(content, file.filename)

        # Save to database
        document = Document(
            meeting_id=meeting_id,
            user_id=current_user.id,
            filename=doc_data["filename"],
            file_type=doc_data["file_type"],
            content=doc_data["content"],
            file_size=doc_data["file_size"],
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        logger.info(f"✓ Document saved: {document.id}")

        return {
            "id": document.id,
            "filename": document.filename,
            "file_type": document.file_type,
            "file_size": document.file_size,
            "created_at": document.created_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading document: {str(e)}",
        )


@router.get("/meetings/{meeting_id}/documents")
async def get_documents(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get documents for a meeting

    Args:
        meeting_id: Meeting ID
        current_user: Current user
        db: Database session

    Returns:
        List of documents
    """
    try:
        # Verify meeting belongs to user
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

        # Get documents
        documents = (
            db.query(Document)
            .filter(Document.meeting_id == meeting_id)
            .order_by(Document.created_at.desc())
            .all()
        )

        return {
            "documents": [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "file_type": doc.file_type,
                    "file_size": doc.file_size,
                    "created_at": doc.created_at.isoformat(),
                }
                for doc in documents
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching documents: {str(e)}",
        )


@router.delete("/meetings/{meeting_id}/documents/{document_id}")
async def delete_document(
    meeting_id: int,
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document

    Args:
        meeting_id: Meeting ID
        document_id: Document ID
        current_user: Current user
        db: Database session

    Returns:
        Success message
    """
    try:
        # Verify meeting belongs to user
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

        # Get and delete document
        document = (
            db.query(Document)
            .filter(
                Document.id == document_id,
                Document.meeting_id == meeting_id,
                Document.user_id == current_user.id,
            )
            .first()
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        db.delete(document)
        db.commit()

        logger.info(f"✓ Document deleted: {document_id}")

        return {"message": "Document deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting document: {str(e)}",
        )
