"""
Vector Memory Provider

A MemoryProvider that stores dense vector embeddings alongside records and
performs cosine-similarity ranking for semantic search.

No external vector database is required. All computation is pure Python.

Architecture Layer: Core / Memory / Providers
"""

import math
from typing import Dict, List, Tuple

from core.memory.interfaces.provider import MemoryProvider
from core.models.memory import (
    MemoryQuery,
    MemoryRecord,
    MemoryResult,
    MemoryStatistics,
)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two equal-length unit-norm vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


class VectorMemoryProvider(MemoryProvider):
    """
    MemoryProvider backed by in-process cosine-similarity search.

    Each MemoryRecord is expected to carry a pre-computed embedding in its
    ``embedding`` field.  Records without embeddings are stored but excluded
    from semantic search results.
    """

    def __init__(self) -> None:
        # Map record_id -> MemoryRecord
        self._store: Dict[str, MemoryRecord] = {}

    # ------------------------------------------------------------------ #
    # Write operations                                                      #
    # ------------------------------------------------------------------ #

    def store(self, record: MemoryRecord) -> None:
        """Persist record (with or without an embedding)."""
        self._store[record.id] = record

    def update(self, record: MemoryRecord) -> None:
        """Replace an existing record (matched by id)."""
        self._store[record.id] = record

    def delete(self, record_id: str) -> None:
        """Remove record. No-op if not found."""
        self._store.pop(record_id, None)

    # ------------------------------------------------------------------ #
    # Read operations                                                       #
    # ------------------------------------------------------------------ #

    def retrieve(self, query: MemoryQuery) -> List[MemoryResult]:
        """Filter records using structured metadata predicates."""
        results: List[MemoryResult] = []

        for record in self._store.values():
            matched_fields: List[str] = []
            reason_parts: List[str] = []

            if query.record_types and record.record_type not in query.record_types:
                continue
            if query.record_types:
                matched_fields.append("record_type")

            if query.tags and not set(query.tags).issubset(set(record.metadata.tags)):
                continue
            if query.tags:
                matched_fields.append("tags")

            if query.goal_id and record.metadata.goal_id != query.goal_id:
                continue
            if query.goal_id:
                matched_fields.append("goal_id")
                reason_parts.append(f"goal_id={query.goal_id}")

            if query.task_id and record.metadata.task_id != query.task_id:
                continue
            if query.task_id:
                matched_fields.append("task_id")
                reason_parts.append(f"task_id={query.task_id}")

            if query.attributes:
                match = all(
                    record.metadata.attributes.get(k) == v for k, v in query.attributes.items()
                )
                if not match:
                    continue
                matched_fields.append("attributes")

            results.append(
                MemoryResult(
                    record=record,
                    relevance_score=1.0,
                    matched_fields=matched_fields,
                    match_reason="; ".join(reason_parts) if reason_parts else None,
                )
            )

        results.sort(key=lambda r: r.record.timestamp, reverse=True)
        return results[: query.top_k]

    def search(self, query: MemoryQuery) -> List[MemoryResult]:
        """
        Semantic search via cosine similarity.

        The query must carry a pre-computed embedding in ``query.text``
        representation — callers should populate record embeddings via the
        EmbeddingProvider before calling this method.  Records without
        embeddings are scored 0.0.

        To allow the service layer to pass the query embedding, this provider
        reads it from ``query.attributes["_embedding"]`` (a convention used
        by MemoryService).
        """
        # Pull query embedding from attributes if injected by MemoryService
        query_embedding: List[float] = []
        if query.attributes:
            raw = query.attributes.get("_embedding")
            if isinstance(raw, list):
                query_embedding = raw

        if not query_embedding:
            # Fall back to metadata filtering if no embedding available
            return self.retrieve(query)

        scored: List[Tuple[float, MemoryResult]] = []

        for record in self._store.values():
            # Optional type pre-filter
            if query.record_types and record.record_type not in query.record_types:
                continue

            if not record.embedding:
                score = 0.0
            else:
                score = _cosine_similarity(query_embedding, record.embedding)

            scored.append(
                (
                    score,
                    MemoryResult(
                        record=record,
                        relevance_score=round(score, 4),
                        matched_fields=["embedding"],
                        match_reason=f"cosine_similarity={score:.4f}",
                    ),
                )
            )

        # Sort descending by score and return top-k
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[: query.top_k]]

    def list(self, record_type: str | None = None) -> List[MemoryRecord]:
        """List all records, optionally filtered by type string."""
        records = list(self._store.values())
        if record_type:
            records = [r for r in records if r.record_type.value == record_type]
        return records

    def statistics(self) -> MemoryStatistics:
        """Compute aggregate statistics."""
        by_type: Dict[str, int] = {}
        for record in self._store.values():
            key = record.record_type.value
            by_type[key] = by_type.get(key, 0) + 1

        return MemoryStatistics(
            total_records=len(self._store),
            records_by_type=by_type,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers                                                      #
    # ------------------------------------------------------------------ #

    def get_by_id(self, record_id: str) -> MemoryRecord | None:
        """Direct id lookup. Useful for test assertions."""
        return self._store.get(record_id)

    def clear(self) -> None:
        """Wipe all records. For test teardown only."""
        self._store.clear()
