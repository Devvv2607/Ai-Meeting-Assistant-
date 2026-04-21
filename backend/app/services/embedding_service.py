# Temporary stub to avoid ML dependencies
# from sentence_transformers import SentenceTransformer
# import numpy as np
from typing import List
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings (stub version without ML dependencies)"""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize embedding model (stub)

        Args:
            model_name: Name of the sentence-transformers model
        """
        logger.warning("Embedding service running in stub mode - embeddings not available")
        self.model = None

    def encode(self, texts: List[str]) -> list:
        """Generate embeddings for list of texts (stub - returns empty list)

        Args:
            texts: List of text strings

        Returns:
            Empty list (stub implementation)
        """
        logger.warning("Embedding generation not available in stub mode")
        return []

    def encode_single(self, text: str) -> list:
        """Generate embedding for single text (stub - returns empty list)

        Args:
            text: Single text string

        Returns:
            Empty list (stub implementation)
        """
        logger.warning("Embedding generation not available in stub mode")
        return []

    def similarity(self, embeddings1: list, embeddings2: list) -> list:
        """Calculate cosine similarity (stub - returns empty list)

        Args:
            embeddings1: First set of embeddings
            embeddings2: Second set of embeddings

        Returns:
            Empty list (stub implementation)
        """
        logger.warning("Similarity calculation not available in stub mode")
        return []


# Global embedding service instance
embedding_service = EmbeddingService()
