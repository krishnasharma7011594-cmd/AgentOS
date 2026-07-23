"""Tests for CapabilityRegistry and AgentRegistry."""

import pytest

from core.exceptions.base import AgentNotFoundError, CapabilityNotFoundError
from core.models.domain import AgentCapability
from registry.agent_registry import AgentRegistry
from registry.capability_registry import CapabilityRegistry


def test_capability_registry_registration_and_lookup() -> None:
    cap_reg = CapabilityRegistry()
    capabilities = [
        AgentCapability(name="web_research", description="Search web"),
        AgentCapability(name="summarization", description="Summarize text"),
    ]

    cap_reg.register_agent_capabilities("ResearchAgent", capabilities)

    assert cap_reg.is_capability_available("web_research") is True
    assert cap_reg.is_capability_available("unknown_capability") is False

    agent_name = cap_reg.find_agent_for_capability("web_research")
    assert agent_name == "ResearchAgent"

    all_caps = cap_reg.list_capabilities()
    assert "web_research" in all_caps
    assert "summarization" in all_caps


def test_capability_registry_not_found() -> None:
    cap_reg = CapabilityRegistry()
    with pytest.raises(CapabilityNotFoundError):
        cap_reg.find_agent_for_capability("non_existent_cap")


def test_agent_registry_operations() -> None:
    agent_reg = AgentRegistry()

    class DummyAgent:
        name = "DummyAgent"
        description = "Dummy description"
        capabilities = [AgentCapability(name="dummy_cap", description="Dummy")]

    dummy = DummyAgent()
    agent_reg.register_agent(dummy.name, dummy)

    assert agent_reg.list_agents() == ["DummyAgent"]
    retrieved = agent_reg.get_agent("DummyAgent")
    assert retrieved is dummy

    with pytest.raises(AgentNotFoundError):
        agent_reg.get_agent("UnknownAgent")
