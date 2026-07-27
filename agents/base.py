"""
Base Agent Interface

Abstract base class defining the lifecycle and execution contract for all AgentOS agents.
Ensures uniform structure and dependency injection across specialized agent implementations.

Phase 4.5: Uses Capability (replacing AgentCapability) and introduces METADATA ClassVar.

Architecture Layer: Agents
"""

from abc import ABC, abstractmethod
from typing import ClassVar, List, Optional

from core.ai.providers.base import BaseLLMProvider
from core.memory.interfaces.base import BaseMemory
from core.models.domain import AgentMetadata, Capability, ExecutionContext, Task, TaskResult
from core.tools.registry import ToolRegistry


class BaseAgent(ABC):
    """
    Abstract Base Class for all autonomous agents in AgentOS.

    Defines constructor dependency injection boundaries (LLM provider, tools, memory)
    and enforces standard lifecycle hooks (`initialize`, `execute_task`, `shutdown`).
    Agents do not reference other agents or the Supervisor directly.

    Phase 4.5: Subclasses declare METADATA: ClassVar[AgentMetadata] to enable
    metadata-driven registry discovery without inspecting agent implementations.
    """

    # Subclasses override with their rich AgentMetadata descriptor.
    METADATA: ClassVar[AgentMetadata]

    def __init__(
        self,
        name: str,
        description: str,
        llm_provider: Optional[BaseLLMProvider] = None,
        capabilities: Optional[List[Capability]] = None,
        tool_registry: Optional[ToolRegistry] = None,
        memory: Optional[BaseMemory] = None,
    ) -> None:
        """
        Initializes BaseAgent attributes.

        Args:
            name:          Canonical agent identifier name.
            description:   Summary of agent role.
            llm_provider:  Injected BaseLLMProvider instance.
            capabilities:  Declared Capability descriptors.
            tool_registry: Optional ToolRegistry reference.
            memory:        Optional BaseMemory adapter.
        """
        self.name = name
        self.description = description
        self.llm_provider = llm_provider
        self.capabilities: List[Capability] = capabilities or []
        self.tool_registry = tool_registry
        self.memory = memory

    @abstractmethod
    async def initialize(self) -> None:
        """Lifecycle hook executed when the agent registers at startup."""
        pass

    @abstractmethod
    async def execute_task(
        self, task: Task, context: Optional[ExecutionContext] = None
    ) -> TaskResult:
        """
        Primary execution entry point called by SupervisorRouter.

        Args:
            task:    Assigned Task definition.
            context: Optional ExecutionContext carrying prior task results.

        Returns:
            TaskResult: Structured execution summary and status payload.
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Lifecycle hook executed during graceful application shutdown."""
        pass
