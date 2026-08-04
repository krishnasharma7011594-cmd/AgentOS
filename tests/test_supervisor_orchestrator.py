"""Tests for SupervisorOrchestrator end-to-end execution flow."""

import pytest

from agents.coding.agent import CodingAgent
from agents.research.agent import ResearchAgent
from core.models.domain import Goal
from core.tools.capability_registry import CapabilityRegistry as ToolCapabilityRegistry
from core.tools.engine import CapabilityEngine
from core.tools.executor import CapabilityExecutor
from core.tools.permissions import PermissionManager
from core.tools.resolver import CapabilityResolver
from core.tools.resources import ResourceManager
from core.tools.sandbox import ToolSandbox
from core.tools.tool_registry import ToolRegistry
from core.utils.helpers import generate_uuid
from registry.agent_registry import AgentRegistry
from registry.capability_registry import CapabilityRegistry as AgentCapabilityRegistry
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
    cap_reg = AgentCapabilityRegistry()
    tool_cap_reg = ToolCapabilityRegistry()
    tool_reg = ToolRegistry()
    perm_mgr = PermissionManager()
    res_mgr = ResourceManager()
    resolver = CapabilityResolver(tool_cap_reg, tool_reg)
    sandbox = ToolSandbox()
    executor = CapabilityExecutor(tool_reg, res_mgr, sandbox)
    cap_engine = CapabilityEngine(tool_cap_reg, perm_mgr, resolver, executor)

    mock_provider = MockLLMProvider(
        "Thought: I know this\nFinal Answer: LangGraph is a stateful multi-agent framework."
    )

    research_agent = ResearchAgent(llm_provider=mock_provider, capability_engine=cap_engine)
    agent_reg.register_agent(research_agent.name, research_agent)
    cap_reg.register_agent_capabilities(research_agent.name, research_agent.capabilities)

    coding_agent = CodingAgent(llm_provider=mock_provider, capability_engine=cap_engine)
    agent_reg.register_agent(coding_agent.name, coding_agent)
    cap_reg.register_agent_capabilities(coding_agent.name, coding_agent.capabilities)

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
    goal = Goal(id=generate_uuid(), description="Research LangGraph and generate a python example")
    result = await orchestrator.execute_goal(goal)

    # 3. Assertions
    assert result.goal_id == goal.id
    assert result.status == "success"
    assert "LangGraph" in result.response
    assert len(result.tasks) == 2

    agent_ids = [t.agent_id for t in result.tasks]
    assert any(a.startswith("ResearchAgent") for a in agent_ids)
    assert any(a.startswith("CodingAgent") for a in agent_ids)

    # Check if first task output is referenced in second task (dependency)
    # The tasks are ordered, so the second one should be CodingAgent.
    assert len(result.tasks[1].metadata["reasoning_steps"]) > 0
