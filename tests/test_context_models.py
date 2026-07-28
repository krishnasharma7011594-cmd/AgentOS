"""
Tests: Context Domain Models
"""

import pytest
from pydantic import ValidationError

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


def test_context_item_immutability():
    item = ContextItem(
        content="Test knowledge",
        source=ContextSource.KNOWLEDGE,
        priority=ContextPriority.NORMAL,
        reason=ContextReason(strategy_name="test", explanation="test"),
        retrieval_strategy="test",
        retrieval_timestamp=1.0,
    )
    with pytest.raises(ValidationError):
        item.content = "New content"


def test_context_bundle_immutability():
    bundle = ContextBundle(
        items=[],
        scope=ContextScope.PLANNER,
        metrics=ContextMetrics(),
    )
    with pytest.raises(ValidationError):
        bundle.scope = ContextScope.AGENT


def test_context_request_defaults():
    req = ContextRequest(
        goal_id="g1",
        goal_description="desc",
        scope=ContextScope.PLANNER,
    )
    assert req.task_id is None
    assert req.selection_policy is None
    assert req.assembly_policy is None


def test_context_bundle_is_empty():
    bundle = ContextBundle(
        items=[],
        scope=ContextScope.PLANNER,
    )
    assert bundle.is_empty
    
    item = ContextItem(
        content="test",
        source=ContextSource.KNOWLEDGE,
        priority=ContextPriority.LOW,
        reason=ContextReason(strategy_name="s", explanation="e"),
        retrieval_strategy="s",
        retrieval_timestamp=0.0,
    )
    bundle_with_items = ContextBundle(
        items=[item],
        scope=ContextScope.PLANNER,
    )
    assert not bundle_with_items.is_empty
