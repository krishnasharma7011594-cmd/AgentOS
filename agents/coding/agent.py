"""CodingAgent implementation."""

from typing import List, Optional

from agents.coding.prompts_v1 import CAPABILITY_TEMPLATES, SYSTEM_CONTEXT
from agents.lifecycle import AgentLifecycle
from core.ai.providers.base import BaseLLMProvider
from core.logging.logger import logger
from core.models.domain import AgentCapability, ExecutionContext, Task, TaskResult
from core.tools.registry import ToolRegistry


class CodingAgent(AgentLifecycle):
    """
    Autonomous agent specialised in software engineering and code generation.

    Registered Capabilities:
        code_generation — generate code snippets or programs
        code_analysis   — analyze architecture and code

    Tools Used:
        None (currently pure LLM generation based on context)

    Prompt Version: v1 (agents/coding/prompts_v1.py)
    Lifecycle: ReAct via AgentLifecycle → ReactReasoner
    """

    CAPABILITIES: List[AgentCapability] = [
        AgentCapability(
            name="code_generation",
            description="Generate production-ready code",
        ),
        AgentCapability(
            name="code_analysis",
            description="Analyze and debug existing codebase",
        ),
    ]

    def __init__(
        self,
        llm_provider: Optional[BaseLLMProvider] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None:
        super().__init__(
            name="CodingAgent",
            description=(
                "Specialized agent for code generation, " "software design, debugging, and testing."
            ),
            llm_provider=llm_provider,
            capabilities=self.CAPABILITIES,
            tool_registry=tool_registry,
        )
        logger.info("coding_agent_init", agent_id=self.agent_id)

    def _setup_tools(self) -> None:
        """
        Register CodingAgent tools.
        For now, no tools are required for simple code generation.
        """
        pass

    def _extra_context(self, context: Optional[ExecutionContext] = None) -> Optional[str]:
        """
        Inject coding-specific guidance into the ReAct user prompt.
        Also injects output from previous tasks if context is provided.
        """
        prompt = SYSTEM_CONTEXT
        if context and context.results:
            prompt += "\n\nPREVIOUS TASK OUTPUTS:\n"
            for _task_id, res in context.results.items():
                prompt += f"\n--- Task ({res.agent_id}) ---\n{res.summary}\n"
        return prompt

    def _max_react_steps(self) -> int:
        """Coding tasks typically just generate code, 3 steps is plenty."""
        return 3

    def get_capabilities(self) -> List[AgentCapability]:
        """Return declared capabilities for registration in CapabilityRegistry."""
        return self.CAPABILITIES

    async def execute_task(
        self, task: Task, context: Optional[ExecutionContext] = None
    ) -> TaskResult:
        """
        Execute a coding task through the ReAct lifecycle.
        """
        logger.info(
            "coding_agent_task_start",
            agent_id=self.agent_id,
            task_id=task.id,
            capability=task.required_capability,
        )

        template = CAPABILITY_TEMPLATES.get(task.required_capability)
        if template:
            task = task.model_copy(
                update={"description": template.format(description=task.description)}
            )

        return await super().execute_task(task, context)
