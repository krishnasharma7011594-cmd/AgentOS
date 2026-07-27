"""
Dynamic Agent Registry

Maintains runtime agent registrations and handles agent discovery by name.
Allows agents to self-register during application setup.

Phase 4.5: Now stores AgentMetadata alongside agent instances, making the
registry fully metadata-driven so the Supervisor can inspect agents without
coupling to implementation classes.

Architecture Layer: Registry
"""

from typing import Any, Dict, List, Optional

from core.exceptions.base import AgentNotFoundError
from core.logging.logger import logger
from core.models.domain import AgentMetadata, Capability


class AgentRegistry:
    """
    Central registry owning all active agent instances and their metadata.

    Responsible for registering agent instances and looking up agents by name.
    Does NOT match capabilities to agents — that responsibility belongs to
    CapabilityRegistry.

    Phase 4.5: Stores AgentMetadata descriptors alongside agent instances.
    """

    def __init__(self) -> None:
        self._agents: Dict[str, Any] = {}
        self._metadata: Dict[str, AgentMetadata] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_name: str,
        agent_instance: Any,
        metadata: Optional[AgentMetadata] = None,
    ) -> None:
        """
        Register an agent instance and optionally its rich metadata.

        If metadata is not supplied, a minimal AgentMetadata is constructed
        from the agent instance's name and description attributes.

        Args:
            agent_name:     Unique string identifier for the agent.
            agent_instance: Instance of BaseAgent subclass.
            metadata:       Optional AgentMetadata descriptor.
        """
        self._agents[agent_name] = agent_instance

        if metadata is not None:
            self._metadata[agent_name] = metadata
        elif hasattr(agent_instance, "METADATA") and isinstance(
            agent_instance.METADATA, AgentMetadata
        ):
            self._metadata[agent_name] = agent_instance.METADATA
        else:
            # Fallback: construct minimal metadata from agent attributes
            self._metadata[agent_name] = AgentMetadata(
                name=agent_name,
                description=getattr(agent_instance, "description", ""),
                capabilities=getattr(agent_instance, "capabilities", []),
            )

        logger.info("AgentRegistry: agent registered", agent=agent_name)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def get_agent(self, agent_name: str) -> Any:
        """
        Retrieve a registered agent instance by name.

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
        """Return a list of all registered agent names."""
        return list(self._agents.keys())

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def get_agent_metadata(self, agent_name: str) -> Optional[AgentMetadata]:
        """Return the AgentMetadata descriptor for an agent, or None."""
        return self._metadata.get(agent_name)

    def list_agent_metadata(self) -> Dict[str, AgentMetadata]:
        """Return a mapping of agent name → AgentMetadata for all registered agents."""
        return dict(self._metadata)

    def get_agent_capabilities(self, agent_name: str) -> List[Capability]:
        """Return Capability objects declared by a registered agent."""
        meta = self._metadata.get(agent_name)
        if meta:
            return meta.capabilities
        agent = self._agents.get(agent_name)
        return getattr(agent, "capabilities", []) if agent else []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Clear all registered agents and metadata. Used in test fixtures."""
        self._agents.clear()
        self._metadata.clear()
