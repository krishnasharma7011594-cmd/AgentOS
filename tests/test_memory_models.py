"""
Tests: Memory Domain Models

Verifies that all Phase 7 domain models are correctly serialisable,
default-populated, and carry the expected field constraints.
"""

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


class TestMemoryRecordType:
    def test_all_values_present(self) -> None:
        values = {m.value for m in MemoryRecordType}
        assert values == {"working", "long_term", "reflection", "knowledge", "execution"}


class TestMemorySource:
    def test_all_values_present(self) -> None:
        values = {m.value for m in MemorySource}
        assert values == {"system", "agent", "user", "reflection", "external"}


class TestMemoryPolicy:
    def test_defaults(self) -> None:
        p = MemoryPolicy()
        assert p.is_ephemeral is False
        assert p.priority == 1
        assert p.ttl_seconds is None

    def test_custom(self) -> None:
        p = MemoryPolicy(ttl_seconds=3600, is_ephemeral=True, priority=5)
        assert p.ttl_seconds == 3600
        assert p.is_ephemeral is True


class TestMemoryMetadata:
    def test_defaults(self) -> None:
        m = MemoryMetadata()
        assert m.source == MemorySource.SYSTEM
        assert m.tags == []
        assert m.attributes == {}
        assert m.goal_id is None

    def test_with_values(self) -> None:
        m = MemoryMetadata(
            source=MemorySource.AGENT,
            tags=["tag1", "tag2"],
            attributes={"key": "value"},
            goal_id="goal-001",
        )
        assert m.source == MemorySource.AGENT
        assert "tag1" in m.tags
        assert m.goal_id == "goal-001"


class TestMemoryRecord:
    def test_auto_id(self) -> None:
        r = MemoryRecord(
            record_type=MemoryRecordType.EXECUTION,
            content="test content",
        )
        assert r.id is not None
        assert len(r.id) == 36  # UUID4

    def test_serialisable(self) -> None:
        r = MemoryRecord(
            record_type=MemoryRecordType.REFLECTION,
            content="reflection text",
        )
        data = r.model_dump()
        assert data["record_type"] == "reflection"
        assert data["content"] == "reflection text"
        assert data["embedding"] is None

    def test_with_embedding(self) -> None:
        r = MemoryRecord(
            record_type=MemoryRecordType.LONG_TERM,
            content="knowledge",
            embedding=[0.1, 0.2, 0.3],
        )
        assert r.embedding == [0.1, 0.2, 0.3]


class TestMemoryQuery:
    def test_defaults(self) -> None:
        q = MemoryQuery()
        assert q.top_k == 5
        assert q.record_types is None
        assert q.text is None

    def test_with_filters(self) -> None:
        q = MemoryQuery(
            text="find similar",
            record_types=[MemoryRecordType.REFLECTION],
            top_k=10,
            goal_id="g-001",
        )
        assert q.top_k == 10
        assert MemoryRecordType.REFLECTION in q.record_types  # type: ignore


class TestMemoryResult:
    def test_with_explanation(self) -> None:
        record = MemoryRecord(
            record_type=MemoryRecordType.KNOWLEDGE,
            content="some doc",
        )
        result = MemoryResult(
            record=record,
            relevance_score=0.95,
            matched_fields=["content", "tags"],
            match_reason="cosine_similarity=0.9500",
        )
        assert result.relevance_score == 0.95
        assert "content" in result.matched_fields
        assert result.match_reason is not None

    def test_defaults(self) -> None:
        record = MemoryRecord(
            record_type=MemoryRecordType.WORKING,
            content="temp",
        )
        result = MemoryResult(record=record, relevance_score=0.5)
        assert result.matched_fields == []
        assert result.match_reason is None


class TestMemoryStatistics:
    def test_structure(self) -> None:
        stats = MemoryStatistics(
            total_records=5,
            records_by_type={"reflection": 3, "execution": 2},
        )
        assert stats.total_records == 5
        assert stats.records_by_type["reflection"] == 3
