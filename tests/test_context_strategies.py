"""
Tests: Context Strategies

Verifies transformation logic and query generation for each strategy.
"""

from core.context.strategies.implementations import (
    ExecutionHistoryStrategy,
    KnowledgeContextStrategy,
    ReflectionContextStrategy,
    SemanticContextStrategy,
)
from core.models.context import (
    ContextPriority,
    ContextRequest,
    ContextScope,
    ContextSource,
)
from core.models.memory import MemoryMetadata, MemoryRecord, MemoryRecordType, MemoryResult


def test_semantic_strategy_build_queries():
    strategy = SemanticContextStrategy()
    request = ContextRequest(
        goal_id="g1", goal_description="Find docs", scope=ContextScope.PLANNER
    )
    queries = strategy.build_queries(request)
    assert len(queries) == 1
    assert queries[0].text == "Find docs"
    assert queries[0].top_k == 5


def test_semantic_strategy_transform():
    strategy = SemanticContextStrategy()
    request = ContextRequest(
        goal_id="g1", goal_description="Find docs", scope=ContextScope.PLANNER
    )
    
    rec1 = MemoryRecord(
        record_type=MemoryRecordType.KNOWLEDGE,
        content="Knowledge content",
        metadata=MemoryMetadata(attributes={"_collection": "knowledge_col"}),
    )
    res1 = MemoryResult(record=rec1, relevance_score=0.9)
    
    items = strategy.transform(request, [res1])
    assert len(items) == 1
    assert items[0].source == ContextSource.KNOWLEDGE
    assert items[0].priority == ContextPriority.NORMAL
    assert items[0].collection == "knowledge_col"
    assert items[0].relevance_score == 0.9


def test_reflection_strategy_build_queries():
    strategy = ReflectionContextStrategy()
    request = ContextRequest(
        goal_id="g2", goal_description="Test replan", scope=ContextScope.SUPERVISOR
    )
    queries = strategy.build_queries(request)
    assert len(queries) == 2
    assert queries[0].goal_id == "g2"
    assert queries[0].record_types == [MemoryRecordType.REFLECTION]
    assert queries[1].text == "Test replan"


def test_reflection_strategy_transform():
    strategy = ReflectionContextStrategy()
    request = ContextRequest(
        goal_id="g2", goal_description="Test", scope=ContextScope.PLANNER
    )
    rec = MemoryRecord(record_type=MemoryRecordType.REFLECTION, content="Ref")
    res = MemoryResult(record=rec, relevance_score=0.95)
    
    items = strategy.transform(request, [res])
    assert len(items) == 1
    assert items[0].source == ContextSource.REFLECTION
    assert items[0].priority == ContextPriority.CRITICAL


def test_execution_history_strategy():
    strategy = ExecutionHistoryStrategy()
    request = ContextRequest(goal_id="g3", goal_description="G", scope=ContextScope.AGENT)
    
    queries = strategy.build_queries(request)
    assert len(queries) == 1
    assert queries[0].goal_id == "g3"
    assert queries[0].record_types == [MemoryRecordType.EXECUTION]
    
    rec = MemoryRecord(record_type=MemoryRecordType.EXECUTION, content="Exec")
    res = MemoryResult(record=rec, relevance_score=1.0)
    
    items = strategy.transform(request, [res])
    assert len(items) == 1
    assert items[0].priority == ContextPriority.HIGH


def test_knowledge_strategy():
    strategy = KnowledgeContextStrategy()
    request = ContextRequest(
        goal_id="g4",
        goal_description="G",
        task_description="T",
        scope=ContextScope.AGENT
    )
    
    queries = strategy.build_queries(request)
    assert len(queries) == 2
    assert queries[0].text == "G"
    assert queries[1].text == "T"
    
    rec = MemoryRecord(record_type=MemoryRecordType.KNOWLEDGE, content="Know")
    res = MemoryResult(record=rec, relevance_score=0.8)
    
    items = strategy.transform(request, [res])
    assert len(items) == 1
    assert items[0].priority == ContextPriority.NORMAL
