from typing import List, Optional
from core.models.capability import CapabilityRequest, ResolvedCapability
from core.tools.capability_registry import CapabilityRegistry
from core.tools.tool_registry import ToolRegistry
from core.exceptions.base import CapabilityNotFoundError
from core.logging.logger import logger


class CapabilityResolver:
    """
    Selects the best tool implementation for a requested capability.
    Handles version negotiation, priority, health, and compatibility.
    """

    def __init__(
        self,
        capability_registry: CapabilityRegistry,
        tool_registry: ToolRegistry
    ) -> None:
        self._capability_registry = capability_registry
        self._tool_registry = tool_registry

    def resolve(self, request: CapabilityRequest) -> ResolvedCapability:
        """
        Resolve a capability request into a specific tool implementation.
        """
        descriptor = self._capability_registry.get(request.capability_name)
        if not descriptor:
            raise CapabilityNotFoundError(f"Capability '{request.capability_name}' is not registered.")

        # Find all tools that expose this capability
        candidate_tools = []
        for tool in self._tool_registry.list_tools():
            manifest = tool.get_manifest()
            if request.capability_name in manifest.capabilities:
                candidate_tools.append(tool)

        if not candidate_tools:
            raise CapabilityNotFoundError(f"No tool implements capability '{request.capability_name}'.")

        # Basic filtering based on health and version
        valid_tools = []
        for tool in candidate_tools:
            manifest = tool.get_manifest()
            health = self._tool_registry.get_health(manifest.name)

            # Skip unhealthy tools
            if health and health.status == "UNHEALTHY":
                continue

            # Check version compatibility if minimum is specified
            if request.minimum_version and not manifest.version.is_compatible_with(request.minimum_version):
                continue

            # If preferred version is specified, we might prioritize it, but for now just filter
            # (In a more complex resolver, we'd score the tools instead of hard filtering).
            
            valid_tools.append(tool)

        if not valid_tools:
            raise CapabilityNotFoundError(f"No compatible, healthy tool for capability '{request.capability_name}'.")

        # Pick the first valid tool (in reality, could sort by priority/health/latency)
        best_tool = valid_tools[0]
        best_manifest = best_tool.get_manifest()

        logger.info(
            "capability_resolved",
            capability=request.capability_name,
            tool=best_manifest.name,
            version=str(best_manifest.version)
        )

        return ResolvedCapability(
            request=request,
            descriptor=descriptor,
            tool_name=best_manifest.name,
            tool_version=best_manifest.version
        )
