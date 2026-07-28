"""
In-Memory Provider

A lightweight, non-persistent MemoryProvider backed by Python dictionaries.

Use cases:
  - Unit testing and CI environments.
  - Ephemeral executions that do not require cross-run persistence.

Architecture Layer: Core / Memory / Providers
"""

from typing import Dict, List

from core.memory.interfaces.provider import MemoryProvider
from core.models.memory import (
    MemoryQuery,
    MemoryRecord,
    MemoryRecordType,
    MemoryResult,
    MemoryStatistics,
)


class InMemoryProvider(MemoryProvider):
    """
    Thread-unsafe in-process memory provider backed by a plain dict.

    Suitable for testing and single-threaded scenarios only.
    """

    def __init__(self) -> None:
        self._store: Dict[str, MemoryRecord] = {}

    # ------------------------------------------------------------------ #
    # Write operations                                                      #
    # ------------------------------------------------------------------ #

    def store(self, record: MemoryRecord) -> None:
        """Persist record to the internal dict."""
        self._store[record.id] = record

    def update(self, record: MemoryRecord) -> None:
        """Overwrite an existing record by ID (silently insert if absent)."""
        self._store[record.id] = record

    def delete(self, record_id: str) -> None:
        """Remove a record by ID. No-op if not found."""
        self._store.pop(record_id, None)

    # ------------------------------------------------------------------ #
    # Read operations                                                       #
    # ------------------------------------------------------------------ #

    def retrieve(self, query: MemoryQuery) -> List[MemoryResult]:
        """
        Filter records by type, tags, goal_id, task_id, and attribute matches.

        Returns results ordered by recency (most recent first).
        """
        results: List[MemoryResult] = []

        for record in self._store.values():
            matched_fields: List[str] = []
            reason_parts: List[str] = []

            # Type filter
            if query.record_types:
                if record.record_type not in query.record_types:
                    continue
                matched_fields.append("record_type")

            # Tag filter
            if query.tags:
                if not set(query.tags).issubset(set(record.metadata.tags)):
                    continue
                matched_fields.append("tags")

            # goal_id filter
            if query.goal_id:
                if record.metadata.goal_id != query.goal_id:
                    continue
                matched_fields.append("goal_id")
                reason_parts.append(f"goal_id={query.goal_id}")

            # task_id filter
            if query.task_id:
                if record.metadata.task_id != query.task_id:
                    continue
                matched_fields.append("task_id")
                reason_parts.append(f"task_id={query.task_id}")

            # Attribute filter
            if query.attributes:
                attr_match = all(
                    record.metadata.attributes.get(key) == val
                    for key, val in query.attributes.items()
                )
                if not attr_match:
                    continue
                matched_fields.append("attributes")
                reason_parts.append("attribute match")

            results.append(
                MemoryResult(
                    record=record,
                    relevance_score=1.0,
                    matched_fields=matched_fields,
                    match_reason="; ".join(reason_parts) if reason_parts else None,
                )
            )

        # Most-recent first, then truncate to top_k
        results.sort(key=lambda r: r.record.timestamp, reverse=True)
        return results[: query.top_k]

    def search(self, query: MemoryQuery) -> List[MemoryResult]:
        """
        Naive substring search over record content.

        The InMemoryProvider does not compute cosine similarity — use
        VectorMemoryProvider for semantic search.
        """
        if not query.text:
            return self.retrieve(query)

        text_lower = query.text.lower()
        results: List[MemoryResult] = []

        for record in self._store.values():
            if text_lower in record.content.lower():
                results.append(
                    MemoryResult(
                        record=record,
                        relevance_score=0.5,
                        matched_fields=["content"],
                        match_reason=f"substring match: '{query.text}'",
                    )
                )

        results.sort(key=lambda r: r.record.timestamp, reverse=True)
        return results[: query.top_k]

    def list(self, record_type: str | None = None) -> List[MemoryRecord]:
        """Return all records, optionally filtered by record_type string."""
        records = list(self._store.values())
        if record_type:
            records = [r for r in records if r.record_type == record_type]
        return records

    def statistics(self) -> MemoryStatistics:
        """Return aggregate statistics for this provider."""
        by_type: Dict[str, int] = {}
        for record in self._store.values():
            key = record.record_type.value
            by_type[key] = by_type.get(key, 0) + 1

        return MemoryStatistics(
            total_records=len(self._store),
            records_by_type=by_type,
        )

    # ------------------------------------------------------------------ #
    # Testing helpers                                                        #
    # ------------------------------------------------------------------ #

    def clear(self) -> None:
        """Wipe all records. For use in test teardown only."""
        self._store.clear()

    def get_by_id(self, record_id: str) -> MemoryRecord | None:
        """Direct lookup by id. For test assertions."""
        return self._store.get(record_id)

    def all_types(self) -> List[MemoryRecordType]:
        """Return unique record types present. For test assertions."""
        return list({r.record_type for r in self._store.values()})
