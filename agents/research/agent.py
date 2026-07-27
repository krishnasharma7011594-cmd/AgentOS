"""
Research Agent — Phase 3 / Phase 4.5 Implementation

The Research Agent is the first true tool-using agent in AgentOS.

Phase 3 elevated it into a full ReAct agent:
  - Registers the WebSearchTool into a ToolRegistry at startup.
  - Delegates all reasoning to ReactReasoner via AgentLifecycle.
  - Can search the web, observe results, and reason across multiple steps.

Phase 4.5 adds:
  - METADATA: ClassVar[AgentMetadata] for metadata-driven registry discovery.
  - Uses Capability (replacing the former AgentCapability model).
  - _extra_context() injects ExecutionContext results from prior tasks.

Architecture Layer: Agents / Research
"""

from typing import ClassVar, List, Optional

from agents.lifecycle import AgentLifecycle
from agents.research.prompts_v1 import CAPABILITY_TEMPLATES, SYSTEM_CONTEXT
from core.ai.providers.base import BaseLLMProvider
from core.logging.logger import logger
from core.models.domain import (
    AgentMetadata,
    Capability,
    ExecutionContext,
    Task,
    TaskResult,
)
from core.tools.implementations.web_search import WebSearchTool
from core.tools.registry import ToolRegistry


class ResearchAgent(AgentLifecycle):
    """
    Autonomous agent specialised in research, documentation lookup, and summarization.

    Registered Capabilities:
        web_research          — research topics using live web search
        documentation_lookup  — explain technical concepts and docs
        summarization         — condense provided information

    Tools Used:
        web_search (WebSearchTool via ToolRegistry)

    Prompt Version: v1 (agents/research/prompts_v1.py)
    Lifecycle: ReAct via AgentLifecycle → ReactReasoner
    """

    CAPABILITIES: List[Capability] = [
        Capability(
            name="web_research",
            description="Research topics and return structured summaries using web search and LLM.",
            version="1.0",
            priority=10,
        ),
        Capability(
            name="documentation_lookup",
            description="Look up documentation and explain technical concepts.",
            version="1.0",
            priority=10,
        ),
        Capability(
            name="summarization",
            description="Summarize provided text or research findings.",
            version="1.0",
            priority=10,
        ),
    ]

    METADATA: ClassVar[AgentMetadata] = AgentMetadata(
        name="ResearchAgent",
        description="Autonomous agent specialised in web research and summarization.",
        version="1.0",
        author="AgentOS",
        capabilities=CAPABILITIES,
        supported_tools=["web_search"],
    )

    def __init__(
        self,
        llm_provider: Optional[BaseLLMProvider] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None:
        super().__init__(
            name="ResearchAgent",
            description="Autonomous agent specialised in web research and summarization.",
            llm_provider=llm_provider,
            capabilities=self.CAPABILITIES,
            tool_registry=tool_registry,
        )
        logger.info("research_agent_init", agent_id=self.agent_id)

    # ------------------------------------------------------------------
    # AgentLifecycle Hooks
    # ------------------------------------------------------------------

    def _setup_tools(self) -> None:
        """
        Register the WebSearchTool.

        Called by AgentLifecycle before each ReAct run.
        Registering on every call is intentional — it is idempotent
        (ToolRegistry.register overwrites on duplicate names) and makes the
        agent safe for hot-reload scenarios in Phase 5+.
        """
        self.tool_registry.register(WebSearchTool())
        logger.debug("research_agent_tools_registered", agent_id=self.agent_id)

    def _extra_context(self, context: Optional[ExecutionContext] = None) -> Optional[str]:
        """
        Inject research-specific guidance into the ReAct user prompt.
        Also injects output from previous tasks if context is provided.
        """
        prompt = SYSTEM_CONTEXT
        if context and context.results:
            prompt += "\n\nPREVIOUS TASK OUTPUTS:\n"
            for _task_id, res in context.results.items():
                prompt += f"\n--- Task ({res.agent_id}) ---\n{res.summary}\n"
        return prompt

    def _max_react_steps(self) -> int:
        """
        Research tasks allow up to 3 reasoning cycles.

        This is enough for: look up a topic → observe → synthesise answer.
        Increase for deeper research workflows in later phases.
        """
        return 3

    # ------------------------------------------------------------------
    # Capability Registration (called by DI container at startup)
    # ------------------------------------------------------------------

    def get_capabilities(self) -> List[Capability]:
        """Return declared capabilities for registration in CapabilityRegistry."""
        return self.CAPABILITIES

    # ------------------------------------------------------------------
    # Task Execution — delegates to AgentLifecycle
    # ------------------------------------------------------------------

    async def execute_task(
        self, task: Task, context: Optional[ExecutionContext] = None
    ) -> TaskResult:
        """
        Execute a research task through the ReAct lifecycle.

        Applies the appropriate prompt template based on the task's required
        capability before delegating to AgentLifecycle.execute_task().
        """
        logger.info(
            "research_agent_task_start",
            agent_id=self.agent_id,
            task_id=task.id,
            capability=task.required_capability,
        )

        # Apply capability-specific prompt template to frame the task correctly
        template = CAPABILITY_TEMPLATES.get(task.required_capability)
        if template:
            task = task.model_copy(
                update={"description": template.format(description=task.description)}
            )

        # Delegate to the shared AgentLifecycle ReAct loop
        return await super().execute_task(task, context)
