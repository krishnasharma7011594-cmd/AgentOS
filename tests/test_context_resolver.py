"""
Tests: Context Resolver
"""

from unittest.mock import MagicMock

from core.context.resolver import ContextResolver
from core.context.strategies.base import ContextStrategy
from core.memory.service import MemoryService
from core.models.context import ContextItem, ContextPriority, ContextReason, ContextRequest, ContextScope, ContextSource
from core.models.memory import MemoryQuery, MemoryRecord, MemoryRecordType, MemoryResult


class MockStrategy(ContextStrategy):
    @property
    def name(self) -> str:
        return "mock_strategy"
        
    def __init__(self):
        self.queries_built = 0
        self.transform_called = 0

    def build_queries(self, request):
        self.queries_built += 1
        return [MemoryQuery(text="test query")]

    def transform(self, request, results):
        self.transform_called += 1
        return [
            ContextItem(
                content="test content",
                source=ContextSource.KNOWLEDGE,
                priority=ContextPriority.NORMAL,
                reason=ContextReason(strategy_name="mock", explanation="mock"),
                retrieval_strategy="mock",
                retrieval_timestamp=1.0,
            )
        ]


def test_resolver_executes_strategies():
    mock_memory = MagicMock(spec=MemoryService)
    
    rec = MemoryRecord(record_type=MemoryRecordType.KNOWLEDGE, content="text")
    mock_memory.search.return_value = [MemoryResult(record=rec, relevance_score=0.9)]
    
    mock_strategy = MockStrategy()
    resolver = ContextResolver(memory_service=mock_memory, strategies=[mock_strategy])
    
    req = ContextRequest(goal_id="g1", goal_description="desc", scope=ContextScope.PLANNER)
    
    items = resolver.resolve(req)
    
    assert mock_strategy.queries_built == 1
    assert mock_strategy.transform_called == 1
    assert mock_memory.search.call_count == 1
    assert len(items) == 1
    assert items[0].content == "test content"
