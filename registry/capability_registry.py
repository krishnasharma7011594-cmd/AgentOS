"""
Capability Registry

Maps Capability objects to agent names for dynamic task routing.
Enables the Supervisor to discover which agent provides a required capability
without hardcoding agent dependencies.

Phase 4.5: Upgraded to store full Capability objects (replacing raw strings)
and use priority-based resolution when multiple agents serve the same capability.

Architecture Layer: Registry
"""

from typing import Dict, List, Optional, Set

from core.exceptions.base import CapabilityNotFoundError
from core.logging.logger import logger
from core.models.domain import Capability


class CapabilityRegistry:
    """
    Central index mapping capability names to registered agent names.

    Decouples task requirements from agent implementations. Agents register
    their Capability descriptors at startup; the router queries this registry
    to resolve the correct agent.

    Phase 4.5: Resolution uses Capability.priority — when multiple agents
    provide the same capability the one with the highest priority wins.
    """

    def __init__(self) -> None:
        # capability name → set of agent names that provide it
        self._capability_to_agents: Dict[str, Set[str]] = {}
        # agent name → list of Capability objects it declared
        self._agent_capabilities: Dict[str, List[Capability]] = {}
        # (capability name, agent name) → priority for resolution
        self._priorities: Dict[str, Dict[str, int]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_agent_capabilities(self, agent_name: str, capabilities: List[Capability]) -> None:
        """
        Register capability bindings for an agent.

        Args:
            agent_name:   Canonical name of registering agent.
            capabilities: List of declared Capability descriptors.
        """
        self._agent_capabilities[agent_name] = capabilities
        for cap in capabilities:
            if cap.name not in self._capability_to_agents:
                self._capability_to_agents[cap.name] = set()
                self._priorities[cap.name] = {}
            self._capability_to_agents[cap.name].add(agent_name)
            self._priorities[cap.name][agent_name] = cap.priority
            logger.debug(
                "CapabilityRegistry: capability registered",
                capability=cap.name,
                agent=agent_name,
                priority=cap.priority,
            )

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def find_agent_for_capability(self, capability_name: str) -> str:
        """
        Resolve the name of an agent qualified to execute a required capability.

        When multiple agents provide the same capability, the one with the
        highest priority value is selected. Ties are broken alphabetically
        for determinism.

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
                details=(f"Registered capabilities: {list(self._capability_to_agents.keys())}"),
            )

        priorities = self._priorities.get(capability_name, {})
        # Sort: highest priority first, then alphabetical for ties
        agent_name = sorted(agents, key=lambda a: (-priorities.get(a, 0), a))[0]
        logger.debug(
            "CapabilityRegistry: agent resolved",
            capability=capability_name,
            agent=agent_name,
            priority=priorities.get(agent_name, 0),
        )
        return agent_name

    def find_all_agents_for_capability(self, capability_name: str) -> List[str]:
        """Return all agent names offering a capability, sorted by priority desc."""
        agents = self._capability_to_agents.get(capability_name, set())
        priorities = self._priorities.get(capability_name, {})
        return sorted(agents, key=lambda a: (-priorities.get(a, 0), a))

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_capabilities(self) -> List[str]:
        """Return all registered capability names (sorted)."""
        return sorted(self._capability_to_agents.keys())

    def get_agent_capabilities(self, agent_name: str) -> List[Capability]:
        """Return Capability objects declared by a specific agent."""
        return self._agent_capabilities.get(agent_name, [])

    def get_capability(self, capability_name: str) -> Optional[Capability]:
        """
        Return the highest-priority Capability descriptor for a given name.

        Returns None if no agent provides this capability.
        """
        agents = self.find_all_agents_for_capability(capability_name)
        if not agents:
            return None
        top_agent = agents[0]
        for cap in self._agent_capabilities.get(top_agent, []):
            if cap.name == capability_name:
                return cap
        return None

    def is_capability_available(self, capability_name: str) -> bool:
        """Check if a capability key is registered to at least one agent."""
        return bool(self._capability_to_agents.get(capability_name))

    def clear(self) -> None:
        """Clear all registrations. Used primarily in test fixtures."""
        self._capability_to_agents.clear()
        self._agent_capabilities.clear()
        self._priorities.clear()
