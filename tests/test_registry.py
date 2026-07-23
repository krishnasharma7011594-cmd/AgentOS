"""Tests for dynamic AgentRegistry."""

import pytest

from agents.research.agent import ResearchAgent
from core.exceptions.base import AgentNotFoundError
from registry.agent_registry import AgentRegistry


def test_agent_registry_dynamic_registration():
    registry = AgentRegistry()
    research_agent = ResearchAgent()

    registry.register_agent("ResearchAgent", research_agent)
    assert "ResearchAgent" in registry.list_agents()

    fetched = registry.get_agent("ResearchAgent")
    assert fetched.name == "ResearchAgent"


def test_agent_registry_not_found():
    registry = AgentRegistry()
    with pytest.raises(AgentNotFoundError):
        registry.get_agent("NonExistentAgent")
