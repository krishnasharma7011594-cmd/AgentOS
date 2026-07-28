"""
Tests: Memory Providers

Covers InMemoryProvider and VectorMemoryProvider — storage, filtering,
search, delete, update, statistics, and edge cases.
"""

import math

from core.memory.providers.in_memory import InMemoryProvider
from core.memory.providers.vector import VectorMemoryProvider, _cosine_similarity
from core.models.memory import (
    MemoryMetadata,
    MemoryQuery,
    MemoryRecord,
    MemoryRecordType,
)

# =========================================================================
# Helpers
# =========================================================================


def make_record(
    content: str = "test content",
    record_type: MemoryRecordType = MemoryRecordType.EXECUTION,
    goal_id: str | None = None,
    tags: list[str] | None = None,
    embedding: list[float] | None = None,
) -> MemoryRecord:
    meta = MemoryMetadata(
        goal_id=goal_id,
        tags=tags or [],
    )
    return MemoryRecord(
        record_type=record_type,
        content=content,
        metadata=meta,
        embedding=embedding,
    )


# =========================================================================
# InMemoryProvider
# =========================================================================


class TestInMemoryProvider:
    def setup_method(self) -> None:
        self.provider = InMemoryProvider()

    def test_store_and_retrieve_by_type(self) -> None:
        r = make_record(content="hello", record_type=MemoryRecordType.REFLECTION)
        self.provider.store(r)
        q = MemoryQuery(record_types=[MemoryRecordType.REFLECTION], top_k=5)
        results = self.provider.retrieve(q)
        assert len(results) == 1
        assert results[0].record.id == r.id

    def test_type_filter_excludes_others(self) -> None:
        self.provider.store(make_record(record_type=MemoryRecordType.EXECUTION))
        self.provider.store(make_record(record_type=MemoryRecordType.REFLECTION))
        q = MemoryQuery(record_types=[MemoryRecordType.REFLECTION])
        results = self.provider.retrieve(q)
        assert all(r.record.record_type == MemoryRecordType.REFLECTION for r in results)

    def test_goal_id_filter(self) -> None:
        r1 = make_record(goal_id="g-001")
        r2 = make_record(goal_id="g-002")
        self.provider.store(r1)
        self.provider.store(r2)
        q = MemoryQuery(goal_id="g-001")
        results = self.provider.retrieve(q)
        assert len(results) == 1
        assert results[0].record.id == r1.id

    def test_tag_filter(self) -> None:
        r1 = make_record(tags=["ai", "research"])
        r2 = make_record(tags=["finance"])
        self.provider.store(r1)
        self.provider.store(r2)
        q = MemoryQuery(tags=["ai"])
        results = self.provider.retrieve(q)
        assert len(results) == 1
        assert results[0].record.id == r1.id

    def test_top_k_respected(self) -> None:
        for i in range(10):
            self.provider.store(make_record(content=f"record {i}"))
        q = MemoryQuery(top_k=3)
        results = self.provider.retrieve(q)
        assert len(results) == 3

    def test_delete(self) -> None:
        r = make_record()
        self.provider.store(r)
        self.provider.delete(r.id)
        assert self.provider.get_by_id(r.id) is None

    def test_update(self) -> None:
        r = make_record(content="original")
        self.provider.store(r)
        r.content = "updated"
        self.provider.update(r)
        stored = self.provider.get_by_id(r.id)
        assert stored is not None
        assert stored.content == "updated"

    def test_substring_search(self) -> None:
        self.provider.store(make_record(content="The quick brown fox"))
        self.provider.store(make_record(content="Some unrelated content"))
        q = MemoryQuery(text="quick brown", top_k=5)
        results = self.provider.search(q)
        assert len(results) == 1
        assert results[0].match_reason is not None

    def test_statistics(self) -> None:
        self.provider.store(make_record(record_type=MemoryRecordType.EXECUTION))
        self.provider.store(make_record(record_type=MemoryRecordType.REFLECTION))
        stats = self.provider.statistics()
        assert stats.total_records == 2
        assert stats.records_by_type.get("execution") == 1
        assert stats.records_by_type.get("reflection") == 1

    def test_list_all(self) -> None:
        self.provider.store(make_record())
        self.provider.store(make_record())
        assert len(self.provider.list()) == 2

    def test_list_by_type(self) -> None:
        self.provider.store(make_record(record_type=MemoryRecordType.EXECUTION))
        self.provider.store(make_record(record_type=MemoryRecordType.REFLECTION))
        records = self.provider.list(record_type="execution")
        assert all(r.record_type == MemoryRecordType.EXECUTION for r in records)

    def test_clear(self) -> None:
        self.provider.store(make_record())
        self.provider.clear()
        assert self.provider.statistics().total_records == 0

    def test_matched_fields_populated(self) -> None:
        r = make_record(goal_id="g-xyz")
        self.provider.store(r)
        q = MemoryQuery(goal_id="g-xyz")
        results = self.provider.retrieve(q)
        assert "goal_id" in results[0].matched_fields


# =========================================================================
# VectorMemoryProvider
# =========================================================================


class TestCosineSimiliarity:
    def test_identical_vectors(self) -> None:
        v = [1.0, 0.0, 0.0]
        assert math.isclose(_cosine_similarity(v, v), 1.0)

    def test_orthogonal_vectors(self) -> None:
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert math.isclose(_cosine_similarity(a, b), 0.0)

    def test_opposite_vectors(self) -> None:
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert math.isclose(_cosine_similarity(a, b), -1.0)

    def test_empty_returns_zero(self) -> None:
        assert _cosine_similarity([], []) == 0.0

    def test_mismatched_dims_returns_zero(self) -> None:
        assert _cosine_similarity([1.0], [1.0, 2.0]) == 0.0


class TestVectorMemoryProvider:
    def setup_method(self) -> None:
        self.provider = VectorMemoryProvider()

    def test_store_and_retrieve_by_type(self) -> None:
        r = make_record(record_type=MemoryRecordType.REFLECTION, embedding=[1.0, 0.0])
        self.provider.store(r)
        q = MemoryQuery(record_types=[MemoryRecordType.REFLECTION])
        results = self.provider.retrieve(q)
        assert len(results) == 1
        assert results[0].record.id == r.id

    def test_semantic_search_cosine(self) -> None:
        # Records with distinct embeddings
        r1 = make_record(content="python code", embedding=[1.0, 0.0, 0.0])
        r2 = make_record(content="finance doc", embedding=[0.0, 1.0, 0.0])
        self.provider.store(r1)
        self.provider.store(r2)

        # Query most similar to r1
        query_emb = [0.99, 0.01, 0.0]
        q = MemoryQuery(text="python", top_k=2, attributes={"_embedding": query_emb})
        results = self.provider.search(q)
        assert results[0].record.id == r1.id
        assert results[0].relevance_score > results[1].relevance_score

    def test_search_without_embedding_falls_back(self) -> None:
        r = make_record(record_type=MemoryRecordType.EXECUTION)
        self.provider.store(r)
        q = MemoryQuery(record_types=[MemoryRecordType.EXECUTION], top_k=5)
        results = self.provider.search(q)
        assert len(results) == 1

    def test_delete(self) -> None:
        r = make_record()
        self.provider.store(r)
        self.provider.delete(r.id)
        assert self.provider.get_by_id(r.id) is None

    def test_update(self) -> None:
        r = make_record(content="before")
        self.provider.store(r)
        r.content = "after"
        self.provider.update(r)
        stored = self.provider.get_by_id(r.id)
        assert stored is not None
        assert stored.content == "after"

    def test_statistics(self) -> None:
        self.provider.store(make_record(record_type=MemoryRecordType.EXECUTION))
        self.provider.store(make_record(record_type=MemoryRecordType.KNOWLEDGE))
        stats = self.provider.statistics()
        assert stats.total_records == 2

    def test_type_filter_in_search(self) -> None:
        r1 = make_record(record_type=MemoryRecordType.REFLECTION, embedding=[1.0, 0.0])
        r2 = make_record(record_type=MemoryRecordType.EXECUTION, embedding=[0.9, 0.1])
        self.provider.store(r1)
        self.provider.store(r2)

        q = MemoryQuery(
            record_types=[MemoryRecordType.REFLECTION],
            top_k=5,
            attributes={"_embedding": [1.0, 0.0]},
        )
        results = self.provider.search(q)
        assert all(r.record.record_type == MemoryRecordType.REFLECTION for r in results)
