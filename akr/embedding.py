"""Embedding engine wrapping fastembed for vector generation.

Converts text into float32 byte vectors compatible with sqlite-vec.
"""

from __future__ import annotations

import struct
from typing import List

from akr.errors import EmbeddingModelError

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384


class EmbeddingEngine:
    """Generates embeddings using fastembed's TextEmbedding model."""

    def __init__(self) -> None:
        """Initialize the fastembed TextEmbedding model.

        Uses the hardcoded model ``BAAI/bge-small-en-v1.5`` (384 dimensions).

        Raises
        ------
        EmbeddingModelError
            If the model cannot be loaded (e.g. fastembed not installed).
        """
        try:
            from fastembed import TextEmbedding  # type: ignore[import-untyped]

            self._model = TextEmbedding(model_name=MODEL_NAME)
        except Exception as exc:
            raise EmbeddingModelError(
                model_name=MODEL_NAME,
                suggestion="Try: pip install fastembed",
            ) from exc

        self._dimensions: int = EMBEDDING_DIM

    def embed(self, text: str) -> bytes:
        """Generate an embedding for *text*.

        Returns sqlite-vec compatible bytes (little-endian float32 array).
        """
        vectors = list(self._model.embed([text]))
        arr = vectors[0]
        return struct.pack(f"<{len(arr)}f", *arr)

    def embed_batch(self, texts: List[str]) -> List[bytes]:
        """Generate embeddings for multiple texts at once."""
        vectors = list(self._model.embed(texts))
        return [struct.pack(f"<{len(v)}f", *v) for v in vectors]

    @property
    def dimensions(self) -> int:
        """Return the embedding dimension count (e.g. 384)."""
        return self._dimensions
