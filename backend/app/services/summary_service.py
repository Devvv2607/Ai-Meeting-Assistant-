"""Service for generating meeting summaries using Groq LLM"""

from typing import Dict, List, Optional
import logging
from app.config import settings
from groq import Groq

logger = logging.getLogger(__name__)


class SummaryService:
    """Service for generating summaries and insights using Groq LLM"""

    def __init__(self):
        """Initialize summary service with Groq client"""
        self.groq_client = None
        self._init_groq()

    def _init_groq(self):
        """Initialize Groq client"""
        try:
            api_key = settings.GROQ_API_KEY
            
            if not api_key or api_key == "":
                logger.error("GROQ_API_KEY not configured for summary generation")
                self.groq_client = None
                return
            
            self.groq_client = Groq(api_key=api_key)
            logger.info("✓ Summary service initialized with Groq LLM")
        except Exception as e:
            logger.error(f"Failed to initialize Groq for summary: {e}")
            self.groq_client = None

    def generate_summary(self, transcript_text: str) -> Optional[Dict]:
        """Generate summary from transcript text using Groq LLM
        
        Args:
            transcript_text: Full transcript text
            
        Returns:
            Dictionary with summary, key_points, action_items, sentiment
        """
        if not self.groq_client:
            logger.error("Groq client not initialized for summary generation")
            return self._get_fallback_summary(transcript_text)
        
        try:
            logger.info(f"Generating summary for {len(transcript_text)} characters of text")
            
            # Create prompt for summary generation
            prompt = f"""Analyze the following meeting transcript and provide:
1. A concise summary (2-3 sentences)
2. Key points (3-5 bullet points)
3. Action items (if any)
4. Overall sentiment (positive, negative, or neutral)

Format your response as JSON with these exact keys:
{{
    "summary": "2-3 sentence summary",
    "key_points": ["point 1", "point 2", "point 3"],
    "action_items": ["action 1", "action 2"],
    "sentiment": "positive|negative|neutral"
}}

Transcript:
{transcript_text}

Provide ONLY the JSON response, no additional text."""

            # Call Groq LLM
            response = self.groq_client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1000,
            )
            
            response_text = response.choices[0].message.content
            logger.info(f"Received summary response from Groq")
            
            # Parse JSON response
            import json
            import re
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                summary_data = json.loads(json_match.group())
                logger.info(f"✓ Summary generated successfully")
                return summary_data
            else:
                logger.warning("Could not parse JSON from summary response")
                return self._get_fallback_summary(transcript_text)
                
        except Exception as e:
            logger.error(f"Error generating summary with Groq: {e}", exc_info=True)
            return self._get_fallback_summary(transcript_text)

    def _get_fallback_summary(self, transcript_text: str) -> Dict:
        """Generate fallback summary when API fails
        
        Args:
            transcript_text: Full transcript text
            
        Returns:
            Dictionary with fallback summary data
        """
        try:
            # Extract first 500 characters as summary
            summary_text = transcript_text[:500]
            if len(transcript_text) > 500:
                summary_text += "..."
            
            # Extract sentences as key points
            sentences = transcript_text.split('. ')[:3]
            key_points = [s.strip() for s in sentences if s.strip()]
            
            logger.info(f"Generated fallback summary")
            
            return {
                "summary": f"Meeting transcript: {summary_text}",
                "key_points": key_points if key_points else ["Meeting content available"],
                "action_items": [],
                "sentiment": "neutral"
            }
        except Exception as e:
            logger.error(f"Error generating fallback summary: {e}")
            return {
                "summary": "Summary generation service temporarily unavailable",
                "key_points": [],
                "action_items": [],
                "sentiment": "neutral"
            }


# Global summary service instance
summary_service = SummaryService()
