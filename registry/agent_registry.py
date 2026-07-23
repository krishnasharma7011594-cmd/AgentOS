"""
Dynamic Agent Registry

Maintains runtime agent registrations and handles agent discovery by name.
Allows agents to self-register during application setup.

Architecture Layer: Registry
"""

from typing import Any, Dict, List

from core.exceptions.base import AgentNotFoundError
from core.logging.logger import logger
from core.models.domain import AgentCapability


class AgentRegistry:
    """
    Central registry owning all active agent instances.

    Responsible for registering agent instances and looking up agents by name.
    Does NOT match capabilities to agents — that responsibility belongs to CapabilityRegistry.
    """

    def __init__(self) -> None:
        self._agents: Dict[str, Any] = {}

    def register_agent(self, agent_name: str, agent_instance: Any) -> None:
        """
        Registers an agent instance under its canonical name.

        Args:
            agent_name: Unique string identifier for the agent.
            agent_instance: Instance of BaseAgent subclass.
        """
        self._agents[agent_name] = agent_instance
        logger.info("AgentRegistry: agent registered", agent=agent_name)

    def get_agent(self, agent_name: str) -> Any:
        """
        Retrieves a registered agent instance by name.

        Args:
            agent_name: Canonical name of the target agent.

        Returns:
            BaseAgent: Initialized agent instance.

        Raises:
            AgentNotFoundError: If agent_name is not registered.
        """
        if agent_name not in self._agents:
            raise AgentNotFoundError(
                f"Agent '{agent_name}' is not registered.",
                details=f"Registered agents: {list(self._agents.keys())}",
            )
        return self._agents[agent_name]

    def list_agents(self) -> List[str]:
        """Returns a list of all registered agent names."""
        return list(self._agents.keys())

    def get_agent_capabilities(self, agent_name: str) -> List[AgentCapability]:
        """Returns declared capabilities for a specific registered agent."""
        agent = self.get_agent(agent_name)
        return getattr(agent, "capabilities", [])

    def clear(self) -> None:
        """Clears all registered agents. Used primarily in test fixtures."""
        self._agents.clear()
