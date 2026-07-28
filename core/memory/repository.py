"""
Knowledge Repository Implementation

Concrete implementation of KnowledgeRepository that bridges MemoryService
with a MemoryProvider using logical collection names as metadata attributes.

Collections map to ``collection`` attribute in MemoryMetadata.attributes.

Architecture Layer: Core / Memory
"""

import time
from typing import Any, Dict, List, Optional

from core.logging.logger import logger
from core.memory.interfaces.provider import MemoryProvider
from core.memory.interfaces.repository import KnowledgeRepository
from core.models.memory import (
    MemoryQuery,
    MemoryRecord,
    MemoryResult,
)

# Logical collections - no hardcoded storage behaviour
COLLECTION_EXECUTIONS = "executions"
COLLECTION_REFLECTIONS = "reflections"
COLLECTION_KNOWLEDGE = "knowledge"
COLLECTION_DOCUMENTS = "documents"

ALL_COLLECTIONS = [
    COLLECTION_EXECUTIONS,
    COLLECTION_REFLECTIONS,
    COLLECTION_KNOWLEDGE,
    COLLECTION_DOCUMENTS,
]


class DefaultKnowledgeRepository(KnowledgeRepository):
    """
    Delegates all storage to the injected MemoryProvider.

    Uses the ``_collection`` key in ``MemoryMetadata.attributes`` to tag
    records with their logical collection, enabling filtered retrieval.
    """

    def __init__(self, provider: MemoryProvider) -> None:
        self._provider = provider
        self._latency_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------ #
    # Write                                                                 #
    # ------------------------------------------------------------------ #

    def add(self, record: MemoryRecord, collection: str) -> None:
        """Tag the record with its collection and delegate to provider."""
        record.metadata.attributes["_collection"] = collection
        start = time.monotonic()
        self._provider.store(record)
        elapsed_ms = (time.monotonic() - start) * 1000
        self._latency_log.append({"op": "add", "collection": collection, "ms": elapsed_ms})
        logger.debug(
            "KnowledgeRepository: stored record",
            record_id=record.id,
            collection=collection,
            latency_ms=round(elapsed_ms, 2),
        )

    def remove(self, record_id: str) -> None:
        """Remove by ID."""
        self._provider.delete(record_id)

    # ------------------------------------------------------------------ #
    # Read                                                                  #
    # ------------------------------------------------------------------ #

    def get(self, record_id: str) -> Optional[MemoryRecord]:
        """Retrieve a single record by its ID via a direct metadata query."""
        results = self._provider.retrieve(MemoryQuery(attributes={"id": record_id}, top_k=1))
        if results:
            return results[0].record
        # Fall back: scan (some providers don't filter on synthetic 'id' attribute)
        for record in self._provider.list():
            if record.id == record_id:
                return record
        return None

    def find(self, query: MemoryQuery, collection: str | None = None) -> List[MemoryResult]:
        """Metadata-filtered retrieval, optionally restricted to a collection."""
        if collection:
            query = query.model_copy(
                update={
                    "attributes": {
                        **(query.attributes or {}),
                        "_collection": collection,
                    }
                }
            )
        start = time.monotonic()
        results = self._provider.retrieve(query)
        elapsed_ms = (time.monotonic() - start) * 1000
        self._latency_log.append({"op": "find", "collection": collection, "ms": elapsed_ms})
        return results

    def semantic_search(
        self,
        query: MemoryQuery,
        collection: str | None = None,
    ) -> List[MemoryResult]:
        """Vector-similarity search, optionally restricted to a collection."""
        if collection:
            query = query.model_copy(
                update={
                    "attributes": {
                        **(query.attributes or {}),
                        "_collection": collection,
                    }
                }
            )
        start = time.monotonic()
        results = self._provider.search(query)
        elapsed_ms = (time.monotonic() - start) * 1000
        self._latency_log.append(
            {"op": "semantic_search", "collection": collection, "ms": elapsed_ms}
        )
        return results

    def list_collection(self, collection: str) -> List[MemoryRecord]:
        """Enumerate all records tagged with the given collection."""
        all_records = self._provider.list()
        return [r for r in all_records if r.metadata.attributes.get("_collection") == collection]

    # ------------------------------------------------------------------ #
    # Observability                                                          #
    # ------------------------------------------------------------------ #

    def get_latency_log(self) -> List[Dict[str, Any]]:
        """Return the recorded operation latencies for observability."""
        return list(self._latency_log)
