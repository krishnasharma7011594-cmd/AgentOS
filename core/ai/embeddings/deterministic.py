"""
Deterministic Embedding Provider

A lightweight, dependency-free embedding provider that generates deterministic
vector embeddings from text using a character-frequency hashing strategy.

Properties:
  - Fully deterministic: same input always produces the same vector.
  - Zero external dependencies.
  - Suitable for testing and local semantic search approximation.
  - Output dimension: 128 floats.

Architecture Layer: Core / AI / Embeddings
"""

import hashlib
import math
from typing import List

from core.ai.embeddings.base import EmbeddingProvider

_DIMENSION = 128


class DeterministicEmbeddingProvider(EmbeddingProvider):
    """
    Produces stable 128-dimensional embeddings from text using deterministic hashing.

    Algorithm:
      1. Tokenise the text by whitespace and lowercase each token.
      2. For each token, compute its SHA-256 digest as bytes.
      3. Map each token digest byte-by-byte to 128 float buckets using modulo.
      4. Accumulate contribution values across all tokens.
      5. Normalise the resulting vector to unit length.

    The resulting vector is consistent across processes and environments.
    """

    def embed_text(self, text: str) -> List[float]:
        """Generate a deterministic 128-dim unit-norm vector for the input text."""
        return _embed(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate deterministic embeddings for a list of texts."""
        return [_embed(t) for t in texts]


def _embed(text: str) -> List[float]:
    """Core embedding logic — tokenise, hash, accumulate, normalise."""
    vector = [0.0] * _DIMENSION

    tokens = text.lower().split() or ["<empty>"]
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for i, byte_val in enumerate(digest):
            bucket = (i * 7 + byte_val) % _DIMENSION
            # Use a signed contribution so similar tokens cluster better
            contribution = (byte_val - 128) / 128.0
            vector[bucket] += contribution

    # L2-normalise
    magnitude = math.sqrt(sum(v * v for v in vector))
    if magnitude > 0:
        vector = [v / magnitude for v in vector]

    return vector
