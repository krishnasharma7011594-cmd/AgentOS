"""Tests for SupervisorOrchestrator end-to-end execution flow."""

import pytest

from agents.research.agent import ResearchAgent
from core.models.domain import Goal
from core.utils.helpers import generate_uuid
from registry.agent_registry import AgentRegistry
from registry.capability_registry import CapabilityRegistry
from supervisor.orchestrator import SupervisorOrchestrator
from supervisor.planner import SupervisorPlanner
from supervisor.report_generator import SupervisorReportGenerator
from supervisor.router import SupervisorRouter
from supervisor.validator import SupervisorValidator
from tests.test_llm_provider import MockLLMProvider


@pytest.mark.asyncio
async def test_supervisor_orchestrator_end_to_end() -> None:
    # 1. Setup DI Graph
    agent_reg = AgentRegistry()
    cap_reg = CapabilityRegistry()
    mock_provider = MockLLMProvider("LangGraph is a stateful multi-agent framework.")

    research_agent = ResearchAgent(llm_provider=mock_provider)
    agent_reg.register_agent(research_agent.name, research_agent)
    cap_reg.register_agent_capabilities(research_agent.name, research_agent.capabilities)

    planner = SupervisorPlanner()
    router = SupervisorRouter(agent_registry=agent_reg, capability_registry=cap_reg)
    validator = SupervisorValidator()
    report_gen = SupervisorReportGenerator()

    orchestrator = SupervisorOrchestrator(
        agent_registry=agent_reg,
        capability_registry=cap_reg,
        planner=planner,
        router=router,
        validator=validator,
        report_generator=report_gen,
    )

    # 2. Execute Goal
    goal = Goal(id=generate_uuid(), description="Research LangGraph")
    result = await orchestrator.execute_goal(goal)

    # 3. Assertions
    assert result.goal_id == goal.id
    assert result.status == "success"
    assert "LangGraph" in result.response
    assert len(result.tasks) == 1
    assert result.tasks[0].agent_id == "ResearchAgent"
