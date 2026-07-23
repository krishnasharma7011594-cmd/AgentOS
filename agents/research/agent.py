"""
Research Agent — Phase 3 Implementation

The Research Agent is the first true tool-using agent in AgentOS.

Phase 2 had a simple LLM wrapper that answered from training data alone.
Phase 3 elevates it into a full ReAct agent:
  - It registers the WebSearchTool into a ToolRegistry at startup.
  - It delegates all reasoning to ReactReasoner via AgentLifecycle.
  - It can search the web, observe results, and reason across multiple steps
    before producing a final answer.

The agent itself owns very little logic — that's intentional. The lifecycle
(AgentLifecycle) owns orchestration; the reasoner (ReactReasoner) owns the
ReAct loop; the tool (WebSearchTool) owns search. ResearchAgent only declares:
  1. What capabilities it exposes to the Supervisor
  2. What tools it needs at runtime
  3. What extra context helps the LLM be a better researcher

Architecture Layer: Agents / Research
"""

from typing import List, Optional

from agents.lifecycle import AgentLifecycle
from agents.research.prompts_v1 import CAPABILITY_TEMPLATES, SYSTEM_CONTEXT
from core.ai.providers.base import BaseLLMProvider
from core.logging.logger import logger
from core.models.domain import AgentCapability, Task, TaskResult
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

    # Capabilities declared to CapabilityRegistry at startup.
    # The Supervisor's Router uses these to match incoming tasks.
    CAPABILITIES: List[AgentCapability] = [
        AgentCapability(
            name="web_research",
            description="Research topics and return structured summaries using web search and LLM.",
        ),
        AgentCapability(
            name="documentation_lookup",
            description="Look up documentation and explain technical concepts.",
        ),
        AgentCapability(
            name="summarization",
            description="Summarize provided text or research findings.",
        ),
    ]

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

    def _extra_context(self) -> Optional[str]:
        """
        Inject research-specific guidance into the ReAct user prompt.

        The SYSTEM_CONTEXT from prompts_v1 nudges the LLM toward well-structured,
        source-citing answers without overriding the generic ReAct system prompt.
        """
        return SYSTEM_CONTEXT

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

    def get_capabilities(self) -> List[AgentCapability]:
        """Return declared capabilities for registration in CapabilityRegistry."""
        return self.CAPABILITIES

    # ------------------------------------------------------------------
    # Task Execution — delegates to AgentLifecycle
    # ------------------------------------------------------------------

    async def execute_task(self, task: Task) -> TaskResult:
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
            # Create a new task with the formatted description
            task = task.model_copy(
                update={"description": template.format(description=task.description)}
            )

        # Delegate to the shared AgentLifecycle ReAct loop
        return await super().execute_task(task)
