"""
Supervisor Router

Dynamically dispatches tasks to registered agent instances via CapabilityRegistry.
Enforces decoupling: the Supervisor never hardcodes agent class references or names.

Architecture Layer: Supervisor / Router
"""

from core.exceptions.base import AgentNotFoundError, CapabilityNotFoundError
from core.logging.logger import logger
from core.models.domain import Task, TaskResult, TaskStatus
from registry.agent_registry import AgentRegistry
from registry.capability_registry import CapabilityRegistry


class SupervisorRouter:
    """
    Supervisor subcomponent owning task-to-agent resolution and task dispatch.

    Uses CapabilityRegistry to discover which agent satisfies `task.required_capability`
    and retrieves the agent instance from AgentRegistry.
    Does NOT construct plans or validate execution outcomes.

    TODO: Support load balancing and capability fallback when multiple agents share a capability.
    """

    def __init__(
        self,
        agent_registry: AgentRegistry,
        capability_registry: CapabilityRegistry,
    ) -> None:
        """
        Initializes SupervisorRouter with injected registries.

        Args:
            agent_registry: AgentRegistry instance.
            capability_registry: CapabilityRegistry instance.
        """
        self.agent_registry = agent_registry
        self.capability_registry = capability_registry

    async def route_task(self, task: Task) -> TaskResult:
        """
        Resolves the appropriate agent for a task and invokes its execution.

        Args:
            task: Task to route and execute.

        Returns:
            TaskResult: Outcome payload produced by the executing agent.
        """
        logger.info(
            "SupervisorRouter: routing task",
            task_id=task.id,
            capability=task.required_capability,
        )

        # 1. Discover agent name via CapabilityRegistry without hardcoding agent references
        try:
            agent_name = self.capability_registry.find_agent_for_capability(
                task.required_capability
            )
        except CapabilityNotFoundError as exc:
            logger.error(
                "SupervisorRouter: capability not found",
                capability=task.required_capability,
                error=str(exc),
            )
            return TaskResult(
                task_id=task.id,
                agent_id="router",
                status=TaskStatus.FAILED,
                summary="",
                error=str(exc),
            )

        # 2. Fetch agent instance from AgentRegistry
        try:
            agent = self.agent_registry.get_agent(agent_name)
        except AgentNotFoundError as exc:
            logger.error(
                "SupervisorRouter: agent not found",
                agent=agent_name,
                error=str(exc),
            )
            return TaskResult(
                task_id=task.id,
                agent_id="router",
                status=TaskStatus.FAILED,
                summary="",
                error=str(exc),
            )

        # 3. Bind assigned agent ID and execute task
        task.assigned_agent_id = agent_name
        logger.info(
            "SupervisorRouter: dispatching to agent",
            task_id=task.id,
            agent=agent_name,
        )

        result: TaskResult = await agent.execute_task(task)
        return result
