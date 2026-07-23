"""
Capability Registry

Maps functional capability keys to agent names.
Enables dynamic task routing: the Supervisor queries this registry to discover which
agent provides a required capability without hardcoding agent dependencies.

Architecture Layer: Registry
"""

from typing import Dict, List, Set

from core.exceptions.base import CapabilityNotFoundError
from core.logging.logger import logger
from core.models.domain import AgentCapability


class CapabilityRegistry:
    """
    Central index mapping capability names (e.g. 'web_research') to registered agent names.

    Decouples task requirements from agent implementations: agents register their declared
    capabilities at startup, and the router queries this registry to resolve the correct agent.
    """

    def __init__(self) -> None:
        self._capability_to_agents: Dict[str, Set[str]] = {}
        self._agent_capabilities: Dict[str, List[AgentCapability]] = {}

    def register_agent_capabilities(
        self, agent_name: str, capabilities: List[AgentCapability]
    ) -> None:
        """
        Registers capability bindings for an agent.

        Args:
            agent_name: Canonical name of registering agent.
            capabilities: List of declared AgentCapability descriptors.
        """
        self._agent_capabilities[agent_name] = capabilities
        for capability in capabilities:
            if capability.name not in self._capability_to_agents:
                self._capability_to_agents[capability.name] = set()
            self._capability_to_agents[capability.name].add(agent_name)
            logger.debug(
                "CapabilityRegistry: capability registered",
                capability=capability.name,
                agent=agent_name,
            )

    def find_agent_for_capability(self, capability_name: str) -> str:
        """
        Resolves the name of an agent qualified to execute a required capability.

        Args:
            capability_name: Required capability key.

        Returns:
            str: Name of matching agent.

        Raises:
            CapabilityNotFoundError: If no registered agent provides the capability.
        """
        agents = self._capability_to_agents.get(capability_name, set())
        if not agents:
            raise CapabilityNotFoundError(
                f"No agent registered for capability: '{capability_name}'.",
                details=f"Registered capabilities: {list(self._capability_to_agents.keys())}",
            )
        # Deterministic resolution: sorts agent names and returns first available match
        agent_name = sorted(agents)[0]
        logger.debug(
            "CapabilityRegistry: agent resolved",
            capability=capability_name,
            agent=agent_name,
        )
        return agent_name

    def find_all_agents_for_capability(self, capability_name: str) -> List[str]:
        """Returns all agent names offering a capability."""
        return sorted(self._capability_to_agents.get(capability_name, set()))

    def list_capabilities(self) -> List[str]:
        """Returns all registered capability names."""
        return sorted(self._capability_to_agents.keys())

    def get_agent_capabilities(self, agent_name: str) -> List[AgentCapability]:
        """Returns capabilities declared by a specific agent."""
        return self._agent_capabilities.get(agent_name, [])

    def is_capability_available(self, capability_name: str) -> bool:
        """Checks if a capability key is registered to at least one agent."""
        return bool(self._capability_to_agents.get(capability_name))
