"""
Embedding Provider Interface

Abstract interface for generating vector embeddings from text.

Architecture Layer: Core / AI / Embeddings
"""

from abc import ABC, abstractmethod
from typing import List


class EmbeddingProvider(ABC):
    """Abstract interface for text embedding models."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """
        Generate an embedding vector for a single string of text.

        Args:
            text: The input string.

        Returns:
            List[float]: The dense vector embedding.
        """
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embedding vectors for a batch of strings.

        Args:
            texts: List of input strings.

        Returns:
            List[List[float]]: List of dense vector embeddings.
        """
        pass
