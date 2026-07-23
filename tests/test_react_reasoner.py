"""Tests for ReactReasoner parsing and ReAct execution loop."""

import pytest

from core.ai.reasoning.react import (
    ReactReasoner,
    _extract_field,
    _parse_llm_output,
    _safe_json_parse,
)
from core.models.domain import Task
from core.tools.base import BaseTool
from core.tools.registry import ToolRegistry
from tests.test_llm_provider import MockLLMProvider


class DummyTool(BaseTool):
    """Simple test tool."""

    def __init__(self) -> None:
        super().__init__(
            name="dummy_tool",
            description="A dummy test tool.",
            parameters={"query": {"type": "string"}},
        )

    async def execute(self, query: str = "", **kwargs) -> str:
        return f"Dummy output for: {query}"


def test_extract_field() -> None:
    text = 'Thought: I should search.\nAction: web_search\nAction Input: {"query": "AgentOS"}'
    assert _extract_field(text, "Thought") == "I should search."
    assert _extract_field(text, "Action") == "web_search"
    assert _extract_field(text, "Action Input") == '{"query": "AgentOS"}'


def test_parse_llm_output_action() -> None:
    text = 'Thought: Need search\nAction: web_search\nAction Input: {"query": "test"}'
    step = _parse_llm_output(text, step=1)
    assert not step.is_final
    assert step.thought == "Need search"
    assert step.action == "web_search"
    assert step.action_input == {"query": "test"}


def test_parse_llm_output_final_answer() -> None:
    text = "Thought: Got the answer\nFinal Answer: AgentOS is an AI OS."
    step = _parse_llm_output(text, step=1)
    assert step.is_final
    assert step.thought == "Got the answer"
    assert step.final_answer == "AgentOS is an AI OS."


def test_safe_json_parse() -> None:
    assert _safe_json_parse('{"key": "val"}') == {"key": "val"}
    assert _safe_json_parse('```json\n{"key": "val"}\n```') == {"key": "val"}
    assert _safe_json_parse("just text") == {"query": "just text"}


@pytest.mark.asyncio
async def test_react_reasoner_direct_final_answer() -> None:
    llm_output = "Thought: I already know this.\nFinal Answer: AgentOS is awesome."
    provider = MockLLMProvider(llm_output)
    registry = ToolRegistry()

    reasoner = ReactReasoner(llm_provider=provider, tool_registry=registry, max_steps=3)
    task = Task(
        goal_id="g-1",
        name="Test Task",
        description="What is AgentOS?",
        required_capability="web_research",
    )

    steps, answer = await reasoner.run(task)
    assert answer == "AgentOS is awesome."
    assert len(steps) == 1
    assert steps[0].is_final


@pytest.mark.asyncio
async def test_react_reasoner_with_tool_call() -> None:
    # First response calls tool, second response gives final answer
    responses = [
        'Thought: Need to search.\nAction: dummy_tool\nAction Input: {"query": "AgentOS"}',
        "Thought: Got output.\nFinal Answer: Found AgentOS details.",
    ]

    class SequenceMockLLMProvider(MockLLMProvider):
        def __init__(self, responses: list[str]) -> None:
            super().__init__("")
            self.responses = responses
            self.call_count = 0

        async def complete(self, messages: list) -> str:
            resp = self.responses[min(self.call_count, len(self.responses) - 1)]
            self.call_count += 1
            return resp

    provider = SequenceMockLLMProvider(responses)
    registry = ToolRegistry()
    registry.register(DummyTool())

    reasoner = ReactReasoner(llm_provider=provider, tool_registry=registry, max_steps=3)
    task = Task(
        goal_id="g-1",
        name="Test Task",
        description="Search AgentOS",
        required_capability="web_research",
    )

    steps, answer = await reasoner.run(task)
    assert answer == "Found AgentOS details."
    assert len(steps) == 2
    assert steps[0].action == "dummy_tool"
    assert "Dummy output for: AgentOS" in (steps[0].observation or "")
    assert steps[1].is_final
