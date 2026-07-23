"""
Agent Lifecycle

Reusable base class that wires the ReAct reasoning loop into any AgentOS agent.

Why this exists:
  Phase 2 agents were thin LLM wrappers that called the provider directly.
  Phase 3 introduces tool use, which requires a consistent lifecycle:
    1. Receive Task
    2. Set up tool registry with agent-specific tools
    3. Delegate to ReactReasoner for the full Think→Act→Observe loop
    4. Package the result into a TaskResult with full reasoning trace

  By putting this lifecycle here in agents/lifecycle.py, we guarantee that
  Coding, GitHub, Finance, and Browser agents can all adopt the same pattern
  in future phases without duplicating the orchestration logic.

Architecture Layer: Agents (shared base)
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional

from agents.base import BaseAgent
from core.ai.providers.base import BaseLLMProvider
from core.ai.reasoning.react import ReactReasoner
from core.exceptions.base import LLMProviderError
from core.logging.logger import logger
from core.models.domain import AgentCapability, ReasoningStep, Task, TaskResult, TaskStatus
from core.tools.registry import ToolRegistry
from core.utils.helpers import generate_uuid


class AgentLifecycle(BaseAgent):
    """
    Reusable lifecycle base for all tool-using AgentOS agents.

    Subclasses must implement:
        _setup_tools()       — register agent-specific tools into self.tool_registry
        _extra_context()     — return optional additional system context for the LLM

    Subclasses may override:
        _max_react_steps()   — how many Think→Act→Observe rounds to allow
    """

    def __init__(
        self,
        name: str = "agent",
        description: str = "AgentOS lifecycle agent",
        llm_provider: Optional[BaseLLMProvider] = None,
        capabilities: Optional[List[AgentCapability]] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None:
        super().__init__(
            name=name,
            description=description,
            llm_provider=llm_provider,
            capabilities=capabilities,
            # Pass an empty registry to BaseAgent; we manage it ourselves below
            tool_registry=None,
        )

        # The tool registry is either injected (production, DI container) or
        # created fresh (unit tests that don't need real tools).
        # We override the one set by BaseAgent so we always have a non-None ref.
        self.tool_registry: ToolRegistry = tool_registry or ToolRegistry()

        # Unique agent instance ID for tracing
        self.agent_id: str = f"{name}-{generate_uuid()[:8]}"

        # ReactReasoner is constructed lazily in execute_task() so it picks up
        # the fully-populated tool_registry after _setup_tools() runs.
        self._reasoner: Optional[ReactReasoner] = None

    # ------------------------------------------------------------------
    # BaseAgent Lifecycle Stubs
    # ------------------------------------------------------------------
    # These are intentionally minimal. Subclasses can override if they need
    # startup/teardown logic (e.g., opening DB connections, loading config).

    async def initialize(self) -> None:
        """Called at agent startup. Override for resource initialisation."""
        logger.info("agent_lifecycle_initialize", agent_id=self.agent_id)

    async def shutdown(self) -> None:
        """Called at graceful shutdown. Override for resource cleanup."""
        logger.info("agent_lifecycle_shutdown", agent_id=self.agent_id)

    # ------------------------------------------------------------------
    # Lifecycle Hooks (subclasses implement / override)
    # ------------------------------------------------------------------

    @abstractmethod
    def _setup_tools(self) -> None:
        """
        Register this agent's tools into self.tool_registry.

        Called exactly once during execute_task() before the ReAct loop starts.
        Subclasses should call self.tool_registry.register(SomeTool()) here.
        """
        ...

    def _extra_context(self) -> Optional[str]:
        """
        Return additional context injected into the first user message.

        Override in subclasses to provide agent-specific guidelines
        (e.g., "Focus on technical accuracy", "Cite sources").
        """
        return None

    def _max_react_steps(self) -> int:
        """Maximum ReAct iterations. Override for agents that need more rounds."""
        return 3

    # ------------------------------------------------------------------
    # Task Execution — the lifecycle entry point
    # ------------------------------------------------------------------

    async def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a task through the full ReAct lifecycle.

        Flow:
            1. _setup_tools() — populate registry (idempotent, safe to re-call)
            2. Construct ReactReasoner with the populated registry
            3. Run the ReAct loop
            4. Package into TaskResult with reasoning trace in metadata

        This method is NOT meant to be overridden. Override the lifecycle
        hooks instead.
        """
        logger.info(
            "agent_lifecycle_start",
            agent_id=self.agent_id,
            task_id=task.id,
            task_name=task.name,
        )

        try:
            # Step 1: populate tool registry
            self._setup_tools()

            # Step 2: build reasoner (rebuilt on each call; tool_registry is shared)
            if self.llm_provider is None:
                raise LLMProviderError(
                    "No LLM provider configured. Inject one via DI or constructor."
                )

            self._reasoner = ReactReasoner(
                llm_provider=self.llm_provider,
                tool_registry=self.tool_registry,
                max_steps=self._max_react_steps(),
            )

            # Step 3: run ReAct loop
            logger.info("agent_lifecycle_react_start", agent_id=self.agent_id, task_id=task.id)
            steps, final_answer = await self._reasoner.run(
                task=task,
                extra_context=self._extra_context(),
            )

            logger.info(
                "agent_lifecycle_complete",
                agent_id=self.agent_id,
                task_id=task.id,
                steps_taken=len(steps),
                answer_length=len(final_answer),
            )

            # Step 4: package result
            return TaskResult(
                task_id=task.id,
                agent_id=self.agent_id,
                status=TaskStatus.SUCCESS,
                summary=final_answer,
                metadata=_build_metadata(steps),
            )

        except Exception as exc:
            logger.error(
                "agent_lifecycle_error",
                agent_id=self.agent_id,
                task_id=task.id,
                error=str(exc),
            )
            return TaskResult(
                task_id=task.id,
                agent_id=self.agent_id,
                status=TaskStatus.FAILED,
                summary=f"Agent failed: {exc}",
                error=str(exc),
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_metadata(steps: List[ReasoningStep]) -> Dict[str, Any]:
    """
    Serialise the reasoning trace into TaskResult.metadata for full traceability.

    The metadata dict is stored alongside the TaskResult and can be surfaced
    in the API response, logs, or observability dashboards.
    """
    return {
        "reasoning_steps": [
            {
                "step": s.step,
                "thought": s.thought,
                "action": s.action,
                "action_input": s.action_input,
                "observation": s.observation,
                "is_final": s.is_final,
            }
            for s in steps
        ],
        "total_steps": len(steps),
    }
