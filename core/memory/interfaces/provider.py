"""
Memory Provider Interface

Abstract interface for memory storage backends.

All concrete providers (InMemoryProvider, VectorMemoryProvider, etc.) must
implement this interface. Application code only depends on MemoryProvider.

Architecture Layer: Core / Memory / Interfaces
"""

from abc import ABC, abstractmethod
from typing import List

from core.models.memory import (
    MemoryQuery,
    MemoryRecord,
    MemoryResult,
    MemoryStatistics,
)


class MemoryProvider(ABC):
    """Abstract storage backend interface for the memory subsystem."""

    @abstractmethod
    def store(self, record: MemoryRecord) -> None:
        """
        Persist a MemoryRecord to the storage backend.

        Args:
            record: The record to store.
        """
        pass

    @abstractmethod
    def retrieve(self, query: MemoryQuery) -> List[MemoryResult]:
        """
        Retrieve matching records via metadata filtering.

        Args:
            query: Structured query filters (types, tags, attributes, goal_id, etc.)

        Returns:
            List of MemoryResult objects ordered by relevance.
        """
        pass

    @abstractmethod
    def delete(self, record_id: str) -> None:
        """
        Remove a record by its ID.

        Args:
            record_id: The record's unique identifier.
        """
        pass

    @abstractmethod
    def update(self, record: MemoryRecord) -> None:
        """
        Replace an existing record with an updated version.

        Args:
            record: The updated record (matched by id).
        """
        pass

    @abstractmethod
    def search(self, query: MemoryQuery) -> List[MemoryResult]:
        """
        Perform semantic search using pre-computed embeddings on the query.

        Args:
            query: A query containing an optional text field and top_k.

        Returns:
            Top-K results ordered by semantic similarity.
        """
        pass

    @abstractmethod
    def list(self, record_type: str | None = None) -> List[MemoryRecord]:
        """
        Enumerate all stored records, optionally filtered by type.

        Args:
            record_type: Optional record type filter.

        Returns:
            List of all matching MemoryRecord objects.
        """
        pass

    @abstractmethod
    def statistics(self) -> MemoryStatistics:
        """
        Return aggregate statistics for this provider.

        Returns:
            MemoryStatistics summary.
        """
        pass
