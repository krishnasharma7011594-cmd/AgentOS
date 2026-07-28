"""
Knowledge Repository Interface

Defines high-level storage operations for distinct logical collections.
Sits between MemoryService (application logic) and MemoryProvider (storage).

Architecture Layer: Core / Memory / Interfaces
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from core.models.memory import MemoryQuery, MemoryRecord, MemoryResult


class KnowledgeRepository(ABC):
    """
    Logical abstraction over a MemoryProvider for collection-aware storage.

    Isolates storage logic from MemoryService so the service never directly
    constructs or interprets storage details.
    """

    @abstractmethod
    def add(self, record: MemoryRecord, collection: str) -> None:
        """
        Add a record to a named collection.

        Args:
            record: The record to store.
            collection: Logical collection name (e.g. 'reflections', 'executions').
        """
        pass

    @abstractmethod
    def get(self, record_id: str) -> Optional[MemoryRecord]:
        """
        Retrieve a single record by its ID.

        Args:
            record_id: The unique identifier of the record.

        Returns:
            The matching MemoryRecord or None.
        """
        pass

    @abstractmethod
    def find(self, query: MemoryQuery, collection: str | None = None) -> List[MemoryResult]:
        """
        Query records from a named collection using metadata filters.

        Args:
            query: Structured query filters.
            collection: Optional collection name to restrict search.

        Returns:
            List of MemoryResult objects.
        """
        pass

    @abstractmethod
    def semantic_search(
        self,
        query: MemoryQuery,
        collection: str | None = None,
    ) -> List[MemoryResult]:
        """
        Perform vector-similarity search across a collection.

        Args:
            query: Query with pre-populated embedding on records.
            collection: Optional collection to restrict search.

        Returns:
            Top-K results ordered by semantic similarity.
        """
        pass

    @abstractmethod
    def remove(self, record_id: str) -> None:
        """
        Delete a record by its ID.

        Args:
            record_id: The unique identifier to remove.
        """
        pass

    @abstractmethod
    def list_collection(self, collection: str) -> List[MemoryRecord]:
        """
        Enumerate all records in a collection.

        Args:
            collection: The logical collection name.

        Returns:
            All records in the collection.
        """
        pass
