from typing import Any

from core.logging.logger import logger
from core.models.capability import CapabilityRequest, CapabilityResult
from core.tools.capability_registry import CapabilityRegistry
from core.tools.executor import CapabilityExecutor
from core.tools.permissions import PermissionManager
from core.tools.resolver import CapabilityResolver


class CapabilityEngine:
    """
    The public entry point for agents to execute capabilities.
    Agents only interact with this class.
    It validates permissions, resolves the capability, and delegates execution.
    """

    def __init__(
        self,
        capability_registry: CapabilityRegistry,
        permission_manager: PermissionManager,
        resolver: CapabilityResolver,
        executor: CapabilityExecutor,
    ) -> None:
        self._capability_registry = capability_registry
        self._permission_manager = permission_manager
        self._resolver = resolver
        self._executor = executor

    async def execute_capability(
        self,
        request: CapabilityRequest,
        agent_id: str = "system",
        supervisor_id: str = "system",
        cancellation_token: Any = None,
    ) -> CapabilityResult:
        """
        Handle the full lifecycle of a capability request from an agent.
        """
        logger.info(
            "capability_engine_received_request", capability=request.capability_name, agent=agent_id
        )

        try:
            # 1. Resolve capability to a specific tool implementation
            resolved_cap = self._resolver.resolve(request)

            # 2. Validate permissions
            self._permission_manager.validate_permissions(
                agent_id=agent_id, required_permissions=resolved_cap.descriptor.permissions
            )

            # 3. Delegate to executor
            result = await self._executor.execute(
                resolved_cap=resolved_cap,
                agent_id=agent_id,
                supervisor_id=supervisor_id,
                cancellation_token=cancellation_token,
            )
            return result

        except Exception as e:
            logger.error(
                "capability_engine_error", capability=request.capability_name, error=str(e)
            )
            return CapabilityResult(success=False, error=str(e))

    def get_capability_descriptions(self) -> str:
        """
        Build a formatted string of capability names and descriptions for injection
        into LLM system prompts.
        """
        capabilities = self._capability_registry.list_capabilities()
        if not capabilities:
            return "No capabilities are currently registered."

        lines = []
        for cap in capabilities:
            lines.append(f"{cap.metadata.name}: {cap.metadata.description}")
            # Note: For full parameter descriptions we'd need parameters schema on the capability.
            # In a robust system, the capability metadata would hold a JSON schema for parameters.
            # For simplicity, we just output the name and description.

        return "\n".join(lines)
