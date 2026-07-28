"""
Memory Service

The single public entry point for the Memory & Knowledge subsystem.

Responsibilities:
  - Embed content via EmbeddingProvider before storage.
  - Delegate all persistence to KnowledgeRepository.
  - Expose domain-aware convenience methods (store_reflection, store_execution, etc.).
  - Collect and expose operational metrics.

The Supervisor and future API layers interact only with MemoryService.
Agents do NOT interact with this class in Phase 7.

Architecture Layer: Core / Memory
"""

import time
import uuid
from typing import Any, Dict, List, Optional

from core.ai.embeddings.base import EmbeddingProvider
from core.logging.logger import logger
from core.memory.interfaces.repository import KnowledgeRepository
from core.memory.repository import (
    COLLECTION_DOCUMENTS,
    COLLECTION_EXECUTIONS,
    COLLECTION_KNOWLEDGE,
    COLLECTION_REFLECTIONS,
)
from core.models.memory import (
    MemoryMetadata,
    MemoryPolicy,
    MemoryQuery,
    MemoryRecord,
    MemoryRecordType,
    MemoryResult,
    MemorySource,
    MemoryStatistics,
)


class MemoryService:
    """
    Application-level facade for the Memory & Knowledge subsystem.

    Components interact only with this class — never with providers or
    repositories directly.

    Metrics tracked:
      - stored_count      – total records written
      - retrieved_count   – total records returned from queries
      - search_latency_ms – cumulative semantic search time
      - embed_latency_ms  – cumulative embedding generation time
    """

    def __init__(
        self,
        repository: KnowledgeRepository,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._repo = repository
        self._embedder = embedding_provider

        # Operational metrics
        self._stored_count = 0
        self._retrieved_count = 0
        self._search_latency_ms = 0.0
        self._embed_latency_ms = 0.0

    # ================================================================== #
    # Core storage API                                                      #
    # ================================================================== #

    def store_record(self, record: MemoryRecord, collection: str) -> MemoryRecord:
        """
        Embed and persist a MemoryRecord in the given collection.

        The record's ``embedding`` field is populated in-place before storage.

        Args:
            record: The record to store.
            collection: Logical collection name.

        Returns:
            The stored record (with embedding populated).
        """
        t_embed_start = time.monotonic()
        record.embedding = self._embedder.embed_text(record.content)
        self._embed_latency_ms += (time.monotonic() - t_embed_start) * 1000

        self._repo.add(record, collection)
        self._stored_count += 1
        logger.info(
            "MemoryService: stored record",
            record_id=record.id,
            type=record.record_type.value,
            collection=collection,
        )
        return record

    # ================================================================== #
    # Domain-aware storage helpers                                          #
    # ================================================================== #

    def store_document(
        self,
        content: str,
        title: str,
        tags: Optional[List[str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> MemoryRecord:
        """
        Store an external document (manual, spec, API description, etc.).

        Args:
            content: Document body.
            title: Human-readable title stored in attributes.
            tags: Optional topic tags.
            attributes: Optional arbitrary key-value metadata.
        """
        record = MemoryRecord(
            id=str(uuid.uuid4()),
            record_type=MemoryRecordType.KNOWLEDGE,
            content=content,
            metadata=MemoryMetadata(
                source=MemorySource.EXTERNAL,
                policy=MemoryPolicy(is_ephemeral=False),
                tags=tags or [],
                attributes={"title": title, **(attributes or {})},
            ),
        )
        return self.store_record(record, COLLECTION_DOCUMENTS)

    def store_execution(
        self,
        goal_id: str,
        summary: str,
        status: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> MemoryRecord:
        """
        Persist a high-level execution summary.

        Args:
            goal_id: The goal ID this execution relates to.
            summary: Natural-language summary of what happened.
            status: Final execution status string.
            attributes: Additional metadata.
        """
        record = MemoryRecord(
            id=str(uuid.uuid4()),
            record_type=MemoryRecordType.EXECUTION,
            content=summary,
            metadata=MemoryMetadata(
                source=MemorySource.SYSTEM,
                policy=MemoryPolicy(is_ephemeral=False),
                tags=["execution", status],
                attributes={"goal_id": goal_id, "status": status, **(attributes or {})},
                goal_id=goal_id,
            ),
        )
        return self.store_record(record, COLLECTION_EXECUTIONS)

    def store_reflection(
        self,
        goal_id: str,
        content: str,
        score: Optional[float] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> MemoryRecord:
        """
        Persist a ReflectionReport (or excerpt) as a searchable memory record.

        Args:
            goal_id: The goal this reflection relates to.
            content: Serialised reflection content (JSON or plain text).
            score: Optional overall reflection score for quick filtering.
            attributes: Additional metadata.
        """
        attrs: Dict[str, Any] = {"goal_id": goal_id, **(attributes or {})}
        if score is not None:
            attrs["score"] = score

        record = MemoryRecord(
            id=str(uuid.uuid4()),
            record_type=MemoryRecordType.REFLECTION,
            content=content,
            metadata=MemoryMetadata(
                source=MemorySource.REFLECTION,
                policy=MemoryPolicy(is_ephemeral=False),
                tags=["reflection"],
                attributes=attrs,
                goal_id=goal_id,
            ),
        )
        return self.store_record(record, COLLECTION_REFLECTIONS)

    def store_knowledge(
        self,
        content: str,
        tags: Optional[List[str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> MemoryRecord:
        """
        Store reusable factual knowledge.

        Args:
            content: The knowledge payload.
            tags: Topic tags.
            attributes: Arbitrary metadata.
        """
        record = MemoryRecord(
            id=str(uuid.uuid4()),
            record_type=MemoryRecordType.KNOWLEDGE,
            content=content,
            metadata=MemoryMetadata(
                source=MemorySource.SYSTEM,
                policy=MemoryPolicy(is_ephemeral=False),
                tags=tags or [],
                attributes=attributes or {},
            ),
        )
        return self.store_record(record, COLLECTION_KNOWLEDGE)

    # ================================================================== #
    # Retrieval API                                                         #
    # ================================================================== #

    def retrieve_by_metadata(
        self,
        query: MemoryQuery,
        collection: Optional[str] = None,
    ) -> List[MemoryResult]:
        """
        Metadata-filtered retrieval.

        Args:
            query: Structured query with filter predicates.
            collection: Optional logical collection restriction.

        Returns:
            List of matching MemoryResult objects.
        """
        results = self._repo.find(query, collection)
        self._retrieved_count += len(results)
        return results

    def retrieve_similar(
        self,
        text: str,
        top_k: int = 5,
        record_types: Optional[List[MemoryRecordType]] = None,
        collection: Optional[str] = None,
    ) -> List[MemoryResult]:
        """
        Semantic similarity search.

        Embeds the query text and delegates to the repository for
        vector-similarity ranking.

        Args:
            text: The query text.
            top_k: Maximum number of results.
            record_types: Optional type filter applied before scoring.
            collection: Optional collection restriction.

        Returns:
            Top-K semantically similar MemoryResult objects.
        """
        t0 = time.monotonic()

        t_embed_start = time.monotonic()
        query_embedding = self._embedder.embed_text(text)
        self._embed_latency_ms += (time.monotonic() - t_embed_start) * 1000

        query = MemoryQuery(
            text=text,
            record_types=record_types,
            top_k=top_k,
            attributes={"_embedding": query_embedding},
        )
        results = self._repo.semantic_search(query, collection)

        self._search_latency_ms += (time.monotonic() - t0) * 1000
        self._retrieved_count += len(results)

        logger.info(
            "MemoryService: semantic search",
            query=text[:80],
            results=len(results),
            collection=collection,
        )
        return results

    def search(
        self,
        text: str,
        top_k: int = 5,
        collection: Optional[str] = None,
    ) -> List[MemoryResult]:
        """
        Hybrid search: semantic similarity + metadata recall, deduplicated.

        Args:
            text: Query text.
            top_k: Maximum results to return.
            collection: Optional collection filter.

        Returns:
            Deduplicated, ranked results.
        """
        semantic_results = self.retrieve_similar(text, top_k, collection=collection)

        # Deduplicate by record id
        seen_ids = {r.record.id for r in semantic_results}

        # Metadata fallback: substring in attributes / tags
        fallback_query = MemoryQuery(text=text, top_k=top_k)
        meta_results = self._repo.find(fallback_query, collection)

        for r in meta_results:
            if r.record.id not in seen_ids:
                seen_ids.add(r.record.id)
                semantic_results.append(r)

        return semantic_results[:top_k]

    def list_collection(self, collection: str) -> List[MemoryRecord]:
        """List all records in a logical collection."""
        return self._repo.list_collection(collection)

    # ================================================================== #
    # Observability                                                         #
    # ================================================================== #

    def get_statistics(self) -> Dict[str, Any]:
        """Return operational metrics for this service instance."""
        return {
            "stored_count": self._stored_count,
            "retrieved_count": self._retrieved_count,
            "search_latency_ms": round(self._search_latency_ms, 2),
            "embed_latency_ms": round(self._embed_latency_ms, 2),
        }

    def provider_statistics(self) -> MemoryStatistics:
        """Delegate to repository for backend-level storage statistics."""
        from core.memory.repository import DefaultKnowledgeRepository

        if isinstance(self._repo, DefaultKnowledgeRepository):
            return self._repo._provider.statistics()

        # Fallback: rough count
        return MemoryStatistics(
            total_records=self._stored_count,
            records_by_type={},
        )
