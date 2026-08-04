import asyncio
import time
from typing import Any, Callable, Coroutine
from core.models.tool import ToolExecutionContext
from core.logging.logger import logger


class ToolExecutionTimeoutError(Exception):
    """Raised when a tool execution exceeds its allowed time."""
    pass


class ToolSandbox:
    """
    Architecturally isolates tool execution.
    Captures exceptions, enforces timeouts, measures execution metrics.
    No containerization in this phase.
    """

    async def execute_in_sandbox(
        self,
        context: ToolExecutionContext,
        execute_fn: Callable[..., Coroutine[Any, Any, Any]],
        **kwargs: Any
    ) -> Any:
        """
        Execute the given coroutine function securely within the sandbox constraints.
        """
        tool_name = context.capability.tool_name
        logger.info(
            "sandbox_execution_start",
            execution_id=context.execution_id,
            tool=tool_name
        )

        start_time = time.monotonic()
        timeout_sec = None

        # Check for timeout policy in the capability descriptor
        if context.capability.descriptor.policy and context.capability.descriptor.policy.timeout_ms:
            timeout_sec = context.capability.descriptor.policy.timeout_ms / 1000.0

        try:
            if timeout_sec:
                # Execute with timeout
                result = await asyncio.wait_for(execute_fn(context=context, **kwargs), timeout=timeout_sec)
            else:
                # Execute unbounded
                result = await execute_fn(context=context, **kwargs)
                
            execution_time_ms = int((time.monotonic() - start_time) * 1000)
            
            logger.info(
                "sandbox_execution_success",
                execution_id=context.execution_id,
                tool=tool_name,
                duration_ms=execution_time_ms
            )
            
            # Record execution time into metadata
            context.execution_metadata["duration_ms"] = execution_time_ms
            
            return result

        except asyncio.TimeoutError as e:
            execution_time_ms = int((time.monotonic() - start_time) * 1000)
            logger.error(
                "sandbox_execution_timeout",
                execution_id=context.execution_id,
                tool=tool_name,
                duration_ms=execution_time_ms
            )
            raise ToolExecutionTimeoutError(f"Tool {tool_name} timed out after {timeout_sec}s.") from e
        except Exception as e:
            execution_time_ms = int((time.monotonic() - start_time) * 1000)
            logger.error(
                "sandbox_execution_failed",
                execution_id=context.execution_id,
                tool=tool_name,
                error=str(e),
                duration_ms=execution_time_ms
            )
            raise
