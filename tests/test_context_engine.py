"""
Tests: Context Engine
"""

from unittest.mock import MagicMock

from core.context.assembler import ContextAssembler
from core.context.engine import ContextEngine
from core.context.ranker import ContextRanker
from core.context.resolver import ContextResolver
from core.models.context import (
    ContextAssemblyPolicy,
    ContextBundle,
    ContextItem,
    ContextMetrics,
    ContextPriority,
    ContextReason,
    ContextRequest,
    ContextScope,
    ContextSource,
)


def test_engine_orchestration():
    mock_resolver = MagicMock(spec=ContextResolver)
    mock_ranker = MagicMock(spec=ContextRanker)
    mock_assembler = MagicMock(spec=ContextAssembler)

    item = ContextItem(
        content="test",
        source=ContextSource.KNOWLEDGE,
        priority=ContextPriority.NORMAL,
        reason=ContextReason(strategy_name="mock", explanation="mock"),
        retrieval_strategy="mock",
        retrieval_timestamp=1.0,
    )
    
    mock_resolver.resolve.return_value = [item]
    mock_ranker.rank.return_value = [item]
    
    expected_bundle = ContextBundle(
        items=[item],
        scope=ContextScope.PLANNER,
        metrics=ContextMetrics(items_retrieved=1, items_discarded=0, generation_latency_ms=10.0)
    )
    mock_assembler.assemble.return_value = expected_bundle

    engine = ContextEngine(
        resolver=mock_resolver,
        ranker=mock_ranker,
        assembler=mock_assembler,
    )

    req = ContextRequest(
        goal_id="g1",
        goal_description="desc",
        scope=ContextScope.PLANNER,
    )

    bundle = engine.build_context(req)

    assert bundle == expected_bundle
    mock_resolver.resolve.assert_called_once_with(req)
    mock_ranker.rank.assert_called_once_with([item])
    mock_assembler.assemble.assert_called_once()
