from typing import Any

from core.logging.logger import logger
from core.models.capability import CapabilityResult, ResolvedCapability
from core.models.tool import ToolExecutionContext
from core.tools.resources import ResourceManager
from core.tools.sandbox import ToolSandbox
from core.tools.tool_registry import ToolRegistry
from core.utils.helpers import generate_uuid


class CapabilityExecutor:
    """
    Handles execution of a ResolvedCapability.
    Acquires resource leases, triggers the ToolSandbox, and executes the tool
    with ToolExecutionContext.
    """

    def __init__(
        self, tool_registry: ToolRegistry, sandbox: ToolSandbox, resource_manager: ResourceManager
    ) -> None:
        self._tool_registry = tool_registry
        self._sandbox = sandbox
        self._resource_manager = resource_manager

    async def execute(
        self,
        resolved_cap: ResolvedCapability,
        agent_id: str = "system",
        supervisor_id: str = "system",
        cancellation_token: Any = None,
    ) -> CapabilityResult:
        """
        Execute the capability via the mapped tool.
        """
        execution_id = generate_uuid()
        tool = self._tool_registry.get_tool(resolved_cap.tool_name)
        manifest = tool.get_manifest()

        logger.info(
            "capability_executor_start",
            execution_id=execution_id,
            capability=resolved_cap.request.capability_name,
            tool=manifest.name,
        )

        acquired_leases = []
        try:
            # 1. Acquire resource leases
            for resource_name in manifest.required_resources:
                # Get duration from policy if present, otherwise default to 300s (5min)
                duration = None
                if resolved_cap.descriptor.policy and resolved_cap.descriptor.policy.timeout_ms:
                    duration = int(resolved_cap.descriptor.policy.timeout_ms / 1000)
                else:
                    duration = 300

                lease = self._resource_manager.acquire_lease(
                    resource_name=resource_name, owner_id=execution_id, duration_sec=duration
                )
                acquired_leases.append(lease)

            # 2. Build Execution Context
            context = ToolExecutionContext(
                execution_id=execution_id,
                request=resolved_cap.request,
                capability=resolved_cap,
                permissions=resolved_cap.descriptor.permissions,
                resource_leases=acquired_leases,
                cancellation_token=cancellation_token,
                agent_id=agent_id,
                supervisor_id=supervisor_id,
            )

            # 3. Execute in Sandbox
            raw_output = await self._sandbox.execute_in_sandbox(
                context=context, execute_fn=tool.execute, **resolved_cap.request.parameters
            )

            # Convert non-string outputs safely or just store as Any
            output = raw_output

            # 4. Cleanup tool state
            await tool.cleanup()

            logger.info(
                "capability_executor_success",
                execution_id=execution_id,
                capability=resolved_cap.request.capability_name,
            )

            return CapabilityResult(
                success=True, output=output, metadata=context.execution_metadata
            )

        except Exception as e:
            logger.error(
                "capability_executor_error",
                execution_id=execution_id,
                capability=resolved_cap.request.capability_name,
                error=str(e),
            )

            # Still attempt cleanup on failure
            try:
                await tool.cleanup()
            except Exception as cleanup_err:
                logger.error("tool_cleanup_failed", error=str(cleanup_err))

            return CapabilityResult(success=False, error=str(e), metadata={})
        finally:
            # 5. Always release leases
            for lease in acquired_leases:
                try:
                    self._resource_manager.release_lease(lease)
                except Exception as e:
                    logger.error("failed_to_release_lease", lease_id=lease.lease_id, error=str(e))
