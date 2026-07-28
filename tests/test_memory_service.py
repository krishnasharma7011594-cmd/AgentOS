"""
Tests: MemoryService

Covers the full MemoryService API including domain helpers, retrieval,
semantic search, hybrid search, and operational metrics.
"""

from core.ai.embeddings.deterministic import DeterministicEmbeddingProvider
from core.memory.providers.in_memory import InMemoryProvider
from core.memory.providers.vector import VectorMemoryProvider
from core.memory.repository import COLLECTION_REFLECTIONS, DefaultKnowledgeRepository
from core.memory.service import MemoryService
from core.models.memory import (
    MemoryQuery,
    MemoryRecord,
    MemoryRecordType,
    MemorySource,
)

# =========================================================================
# Fixtures
# =========================================================================


def _make_service(use_vector: bool = False) -> MemoryService:
    provider = VectorMemoryProvider() if use_vector else InMemoryProvider()
    repo = DefaultKnowledgeRepository(provider=provider)
    embedder = DeterministicEmbeddingProvider()
    return MemoryService(repository=repo, embedding_provider=embedder)


# =========================================================================
# Store / Retrieve
# =========================================================================


class TestMemoryServiceStorage:
    def test_store_record_populates_embedding(self) -> None:
        svc = _make_service()
        record = MemoryRecord(
            record_type=MemoryRecordType.KNOWLEDGE,
            content="Python is a programming language",
        )
        stored = svc.store_record(record, "knowledge")
        assert stored.embedding is not None
        assert len(stored.embedding) == 128  # DeterministicEmbeddingProvider dim

    def test_store_document(self) -> None:
        svc = _make_service()
        record = svc.store_document(
            content="The AgentOS architecture overview",
            title="Architecture Doc",
            tags=["docs"],
        )
        assert record.record_type == MemoryRecordType.KNOWLEDGE
        assert record.metadata.source == MemorySource.EXTERNAL
        assert "docs" in record.metadata.tags
        assert record.metadata.attributes["title"] == "Architecture Doc"

    def test_store_execution(self) -> None:
        svc = _make_service()
        record = svc.store_execution(
            goal_id="g-001",
            summary="Executed research goal",
            status="success",
            attributes={"execution_time_ms": 1234},
        )
        assert record.record_type == MemoryRecordType.EXECUTION
        assert record.metadata.goal_id == "g-001"
        assert "execution" in record.metadata.tags
        assert "success" in record.metadata.tags
        assert record.metadata.attributes["execution_time_ms"] == 1234

    def test_store_reflection(self) -> None:
        svc = _make_service()
        record = svc.store_reflection(
            goal_id="g-002",
            content='{"overall_score": 87}',
            score=87.0,
            attributes={"observation_count": 3},
        )
        assert record.record_type == MemoryRecordType.REFLECTION
        assert record.metadata.source == MemorySource.REFLECTION
        assert record.metadata.attributes["score"] == 87.0
        assert record.metadata.attributes["observation_count"] == 3

    def test_store_knowledge(self) -> None:
        svc = _make_service()
        record = svc.store_knowledge(
            content="Always validate inputs before processing.",
            tags=["best-practice"],
        )
        assert record.record_type == MemoryRecordType.KNOWLEDGE
        assert "best-practice" in record.metadata.tags

    def test_stored_count_increments(self) -> None:
        svc = _make_service()
        svc.store_knowledge("fact one")
        svc.store_knowledge("fact two")
        stats = svc.get_statistics()
        assert stats["stored_count"] == 2


# =========================================================================
# Metadata Retrieval
# =========================================================================


class TestMemoryServiceRetrieval:
    def test_retrieve_by_goal_id(self) -> None:
        svc = _make_service()
        svc.store_execution(goal_id="g-A", summary="done", status="success")
        svc.store_execution(goal_id="g-B", summary="also done", status="success")
        results = svc.retrieve_by_metadata(MemoryQuery(goal_id="g-A", top_k=5))
        assert all(r.record.metadata.goal_id == "g-A" for r in results)
        assert len(results) == 1

    def test_retrieve_by_type(self) -> None:
        svc = _make_service()
        svc.store_reflection(goal_id="g-1", content="reflection")
        svc.store_execution(goal_id="g-1", summary="exec", status="success")
        results = svc.retrieve_by_metadata(
            MemoryQuery(record_types=[MemoryRecordType.REFLECTION], top_k=5)
        )
        assert all(r.record.record_type == MemoryRecordType.REFLECTION for r in results)

    def test_retrieve_by_collection(self) -> None:
        svc = _make_service()
        svc.store_reflection(goal_id="g-x", content="rfl")
        results = svc.retrieve_by_metadata(MemoryQuery(top_k=5), collection=COLLECTION_REFLECTIONS)
        assert all(
            r.record.metadata.attributes.get("_collection") == COLLECTION_REFLECTIONS
            for r in results
        )

    def test_list_collection(self) -> None:
        svc = _make_service()
        svc.store_reflection(goal_id="g-r1", content="reflection 1")
        svc.store_reflection(goal_id="g-r2", content="reflection 2")
        svc.store_execution(goal_id="g-e1", summary="exec", status="success")
        reflections = svc.list_collection(COLLECTION_REFLECTIONS)
        assert len(reflections) == 2
        assert all(
            r.metadata.attributes.get("_collection") == COLLECTION_REFLECTIONS for r in reflections
        )


# =========================================================================
# Semantic Search
# =========================================================================


class TestMemoryServiceSemanticSearch:
    def test_retrieve_similar_returns_results(self) -> None:
        svc = _make_service(use_vector=True)
        svc.store_knowledge("Python is a dynamically typed language", tags=["python"])
        svc.store_knowledge("Java is a statically typed language", tags=["java"])
        results = svc.retrieve_similar("Python programming", top_k=2)
        assert len(results) >= 1

    def test_retrieve_similar_empty_store_returns_empty(self) -> None:
        svc = _make_service(use_vector=True)
        results = svc.retrieve_similar("some query", top_k=5)
        assert results == []

    def test_retrieve_similar_top_k_respected(self) -> None:
        svc = _make_service(use_vector=True)
        for i in range(5):
            svc.store_knowledge(f"fact number {i}")
        results = svc.retrieve_similar("some fact", top_k=2)
        assert len(results) <= 2

    def test_embed_latency_tracked(self) -> None:
        svc = _make_service(use_vector=True)
        svc.store_knowledge("content")
        svc.retrieve_similar("query", top_k=1)
        stats = svc.get_statistics()
        # We stored 1 record and did 1 search, so embed_latency should be > 0
        assert stats["embed_latency_ms"] > 0


# =========================================================================
# Hybrid Search
# =========================================================================


class TestMemoryServiceHybridSearch:
    def test_hybrid_search_combines_results(self) -> None:
        svc = _make_service(use_vector=True)
        svc.store_knowledge("Machine learning fundamentals")
        svc.store_knowledge("Deep learning techniques")
        results = svc.search("learning", top_k=5)
        assert len(results) >= 1

    def test_hybrid_search_deduplicates(self) -> None:
        svc = _make_service(use_vector=True)
        svc.store_knowledge("unique learning content")
        results = svc.search("learning", top_k=5)
        ids = [r.record.id for r in results]
        assert len(ids) == len(set(ids))


# =========================================================================
# Operational Metrics
# =========================================================================


class TestMemoryServiceMetrics:
    def test_statistics_structure(self) -> None:
        svc = _make_service()
        svc.store_execution(goal_id="g-1", summary="exec", status="success")
        stats = svc.get_statistics()
        assert "stored_count" in stats
        assert "retrieved_count" in stats
        assert "search_latency_ms" in stats
        assert "embed_latency_ms" in stats

    def test_retrieved_count_increments(self) -> None:
        svc = _make_service()
        svc.store_execution(goal_id="g-1", summary="exec", status="success")
        svc.retrieve_by_metadata(MemoryQuery(goal_id="g-1", top_k=5))
        stats = svc.get_statistics()
        assert stats["retrieved_count"] >= 1
