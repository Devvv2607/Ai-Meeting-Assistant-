"""Service for meeting Q&A chatbot"""

import logging
from typing import List, Optional, Dict
import json
from app.models.transcript import Transcript
from app.models.document import Document
from app.config import settings

logger = logging.getLogger(__name__)

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


class ChatbotService:
    """Service for answering questions about meetings"""

    def __init__(self):
        self.max_context_length = 4000  # Max characters for context
        self.groq_client = None
        
        if GROQ_AVAILABLE and settings.GROQ_API_KEY:
            self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
        else:
            logger.warning("Groq API not available or API key not set")

    def answer_question(
        self,
        question: str,
        transcripts: List[Transcript],
        documents: Optional[List[Document]] = None,
    ) -> Dict:
        """Answer a question about the meeting using transcript and documents as context

        Args:
            question: User's question
            transcripts: List of transcript segments
            documents: Optional list of uploaded documents

        Returns:
            Dictionary with answer and sources
        """
        try:
            logger.info(f"Processing question: {question}")

            # Build context from transcripts and documents
            context = self._build_context(transcripts, documents)

            # Create prompt
            prompt = self._create_prompt(question, context)

            # Get answer from Groq API
            answer = self._call_groq_api(prompt)

            # Extract sources
            sources = self._extract_sources(question, transcripts, documents)

            logger.info(f"✓ Question answered successfully")

            return {
                "answer": answer,
                "sources": sources,
                "context_used": {
                    "transcript_segments": len(transcripts),
                    "documents": len(documents) if documents else 0,
                },
            }

        except Exception as e:
            logger.error(f"Error answering question: {e}", exc_info=True)
            raise

    def _call_groq_api(self, prompt: str) -> str:
        """Call Groq API to get answer

        Args:
            prompt: Formatted prompt for the LLM

        Returns:
            Answer from Groq API
        """
        try:
            if not self.groq_client:
                raise ValueError("Groq client not initialized")

            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1024,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error calling Groq API: {e}", exc_info=True)
            raise

    def _build_context(
        self, transcripts: List[Transcript], documents: Optional[List[Document]] = None
    ) -> str:
        """Build context from transcripts and documents

        Args:
            transcripts: List of transcript segments
            documents: Optional list of documents

        Returns:
            Context string
        """
        context_parts = []

        # Add transcript context
        if transcripts:
            transcript_text = "\n".join(
                [f"[{self._format_time(t.start_time)}] {t.speaker}: {t.text}" for t in transcripts]
            )
            context_parts.append(f"MEETING TRANSCRIPT:\n{transcript_text}")

        # Add document context
        if documents:
            for doc in documents:
                context_parts.append(f"DOCUMENT ({doc.filename}):\n{doc.content}")

        # Combine and truncate if needed
        context = "\n\n---\n\n".join(context_parts)

        if len(context) > self.max_context_length:
            context = context[: self.max_context_length] + "...[truncated]"

        return context

    def _create_prompt(self, question: str, context: str) -> str:
        """Create prompt for LLM

        Args:
            question: User's question
            context: Context from transcripts and documents

        Returns:
            Formatted prompt
        """
        prompt = f"""You are a helpful assistant answering questions about a meeting and related documents.

CONTEXT:
{context}

QUESTION: {question}

Please provide a clear, concise answer based on the context provided. If the answer is not in the context, say so clearly."""

        return prompt

    def _extract_sources(
        self,
        question: str,
        transcripts: List[Transcript],
        documents: Optional[List[Document]] = None,
    ) -> List[Dict]:
        """Extract relevant sources for the answer

        Args:
            question: User's question
            transcripts: List of transcript segments
            documents: Optional list of documents

        Returns:
            List of source dictionaries
        """
        sources = []

        # Find relevant transcript segments
        question_lower = question.lower()
        for transcript in transcripts:
            if any(
                word in transcript.text.lower()
                for word in question_lower.split()
                if len(word) > 3
            ):
                sources.append(
                    {
                        "type": "transcript",
                        "speaker": transcript.speaker,
                        "time": self._format_time(transcript.start_time),
                        "text": transcript.text[:200] + "..." if len(transcript.text) > 200 else transcript.text,
                    }
                )

        # Find relevant documents
        if documents:
            for doc in documents:
                if any(
                    word in doc.content.lower()
                    for word in question_lower.split()
                    if len(word) > 3
                ):
                    sources.append(
                        {
                            "type": "document",
                            "filename": doc.filename,
                            "text": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                        }
                    )

        return sources[:5]  # Return top 5 sources

    def _format_time(self, seconds: float) -> str:
        """Format seconds to HH:MM:SS

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


# Global chatbot service instance
chatbot_service = ChatbotService()
