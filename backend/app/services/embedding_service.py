from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings for semantic search"""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize embedding model

        Args:
            model_name: Name of the sentence-transformers model
        """
        try:
            self.model = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            raise

    def encode(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for list of texts

        Args:
            texts: List of text strings

        Returns:
            NumPy array of embeddings
        """
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return np.array([])

    def encode_single(self, text: str) -> np.ndarray:
        """Generate embedding for single text

        Args:
            text: Single text string

        Returns:
            NumPy array of embedding
        """
        try:
            embedding = self.model.encode([text], convert_to_numpy=True)
            return embedding[0]
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return np.array([])

    def similarity(self, embeddings1: np.ndarray, embeddings2: np.ndarray) -> np.ndarray:
        """Calculate cosine similarity between embeddings

        Args:
            embeddings1: First set of embeddings
            embeddings2: Second set of embeddings

        Returns:
            Similarity scores
        """
        try:
            similarities = self.model.similarity(embeddings1, embeddings2)
            return similarities.numpy()
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return np.array([])


# Global embedding service instance
embedding_service = EmbeddingService()
