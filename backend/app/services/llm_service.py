from typing import Dict, List, Optional
import json
import logging
import requests
from app.config import settings

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM integration (Gemini, Mistral or LLaMA)"""

    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
        self.provider = settings.LLM_PROVIDER
        
        # Initialize Gemini if provider is gemini
        if self.provider == "gemini" and GENAI_AVAILABLE:
            genai.configure(api_key=self.api_key)

    def generate_summary(self, transcript: str) -> Optional[Dict]:
        """Generate summary from transcript

        Args:
            transcript: Full meeting transcript

        Returns:
            Dictionary with summary, key_points, and action_items
        """
        try:
            prompt = self._build_analysis_prompt(transcript)

            if self.provider == "gemini":
                response = self._call_gemini_api(prompt)
            elif self.provider == "mistral":
                response = self._call_mistral_api(prompt)
            else:
                response = self._call_llama_api(prompt)

            return self._parse_response(response)

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return None

    def _build_analysis_prompt(self, transcript: str) -> str:
        """Build analysis prompt for LLM"""
        return f"""You are an AI meeting assistant. Analyze the following meeting transcript and provide a structured analysis.

TRANSCRIPT:
{transcript}

Please provide ONLY a valid JSON response with the following structure (no additional text):
{{
    "summary": "A 2-3 sentence summary of the meeting",
    "key_points": ["Point 1", "Point 2", "Point 3"],
    "action_items": [
        {{
            "task": "Description of the task",
            "owner": "Person responsible",
            "due_date": "Estimated due date if mentioned"
        }}
    ],
    "sentiment": "positive/neutral/negative"
}}

JSON Response:"""

    def _call_gemini_api(self, prompt: str) -> Optional[str]:
        """Call Google Gemini API
        
        Uses the google-generativeai library for free tier access
        """
        try:
            if not GENAI_AVAILABLE:
                logger.error("google-generativeai library not installed. Install with: pip install google-generativeai")
                return None
            
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt)
            
            if response.text:
                return response.text
            else:
                logger.warning("Empty response from Gemini API")
                return None
                
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return None

    def _call_mistral_api(self, prompt: str) -> Optional[str]:
        """Call Mistral API

        Note: This is a placeholder. Update with actual Mistral API endpoint.
        """
        try:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

            # Using mock response for demonstration
            # Replace with actual Mistral API call
            mock_response = {
                "summary": "This was a productive meeting discussing project milestones and next steps.",
                "key_points": [
                    "Project deadline moved to Q2",
                    "Team needs more resources for development",
                    "Client feedback positive on design",
                ],
                "action_items": [
                    {
                        "task": "Prepare resource plan",
                        "owner": "Manager",
                        "due_date": "End of week",
                    },
                    {
                        "task": "Schedule design review",
                        "owner": "Design Lead",
                        "due_date": "Next Monday",
                    },
                ],
                "sentiment": "positive",
            }

            return json.dumps(mock_response)

        except Exception as e:
            logger.error(f"Error calling Mistral API: {e}")
            return None

    def _call_llama_api(self, prompt: str) -> Optional[str]:
        """Call LLaMA API

        Note: This is a placeholder. Update with actual LLaMA API endpoint.
        """
        try:
            # Using mock response for demonstration
            mock_response = {
                "summary": "This was a productive meeting discussing project milestones and next steps.",
                "key_points": [
                    "Project deadline moved to Q2",
                    "Team needs more resources for development",
                    "Client feedback positive on design",
                ],
                "action_items": [
                    {
                        "task": "Prepare resource plan",
                        "owner": "Manager",
                        "due_date": "End of week",
                    },
                    {
                        "task": "Schedule design review",
                        "owner": "Design Lead",
                        "due_date": "Next Monday",
                    },
                ],
                "sentiment": "positive",
            }

            return json.dumps(mock_response)

        except Exception as e:
            logger.error(f"Error calling LLaMA API: {e}")
            return None

    def _parse_response(self, response: Optional[str]) -> Optional[Dict]:
        """Parse LLM response"""
        if not response:
            return None

        try:
            # Extract JSON from response if wrapped in text
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                json_str = response

            parsed = json.loads(json_str)
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing LLM response: {e}")
            try:
                return json.loads(response)
            except:
                return None


# Global LLM service instance
llm_service = LLMService()
