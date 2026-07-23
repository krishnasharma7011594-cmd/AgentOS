"""
Research Agent Implementation

Specialized agent responsible for researching topics, summarizing information, and
explaining technical concepts using an injected LLM provider.

Architecture Layer: Agents / Research
"""

from typing import List, Optional

from agents.base import BaseAgent
from agents.research.config import ResearchAgentConfig
from agents.research.memory import ResearchAgentMemory
from core.ai.providers.base import BaseLLMProvider
from core.exceptions.base import LLMProviderError
from core.logging.logger import logger
from core.models.domain import AgentCapability, Message, RoleEnum, Task, TaskResult, TaskStatus
from core.utils.helpers import generate_uuid


class ResearchAgent(BaseAgent):
    """
    Autonomous agent specialized in research and summarization tasks.

    Receives tasks assigned by SupervisorRouter, constructs prompts, invokes the injected
    BaseLLMProvider, and packages the LLM completion into a TaskResult.
    """

    # Capabilities declared to CapabilityRegistry at startup
    CAPABILITIES: List[AgentCapability] = [
        AgentCapability(
            name="web_research",
            description="Research topics and return structured summaries using LLM knowledge.",
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
        config: Optional[ResearchAgentConfig] = None,
    ):
        """
        Initializes ResearchAgent with injected dependencies.

        Args:
            llm_provider: Injected LLM provider implementation.
            config: Agent configuration settings.
        """
        cfg = config or ResearchAgentConfig()
        memory = ResearchAgentMemory()
        super().__init__(
            name=cfg.agent_name,
            description="Specialized agent for research, documentation lookup, and summarization.",
            llm_provider=llm_provider,
            capabilities=self.CAPABILITIES,
            memory=memory,
        )
        self.config = cfg

    async def initialize(self) -> None:
        """Startup lifecycle hook."""
        logger.info("ResearchAgent: initialized", agent=self.name)

    async def execute_task(self, task: Task) -> TaskResult:
        """
        Executes an assigned research Task.

        Passes task prompt to the configured LLM provider and returns a structured TaskResult.

        Args:
            task: Target task definition.

        Returns:
            TaskResult: Execution outcome payload.
        """
        logger.info(
            "ResearchAgent: executing task",
            agent=self.name,
            task_id=task.id,
            task_name=task.name,
            capability=task.required_capability,
        )

        if self.llm_provider is None:
            logger.error("ResearchAgent: no LLM provider configured", agent=self.name)
            return TaskResult(
                task_id=task.id,
                agent_id=self.name,
                status=TaskStatus.FAILED,
                summary="",
                error="No LLM provider configured for ResearchAgent.",
            )

        try:
            messages = self._build_messages(task)
            response = await self.llm_provider.generate_response(
                messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            summary = response.content
            provider_meta = response.metadata

            logger.info(
                "ResearchAgent: task completed",
                task_id=task.id,
                summary_chars=len(summary),
            )

            return TaskResult(
                task_id=task.id,
                agent_id=self.name,
                status=TaskStatus.SUCCESS,
                summary=summary,
                metadata={
                    "provider": provider_meta.get("provider", "unknown"),
                    "model": provider_meta.get("model", "unknown"),
                    "capability_used": task.required_capability,
                    "goal_id": task.goal_id,
                },
            )

        except LLMProviderError as exc:
            logger.error(
                "ResearchAgent: LLM provider error",
                task_id=task.id,
                error=str(exc),
            )
            return TaskResult(
                task_id=task.id,
                agent_id=self.name,
                status=TaskStatus.FAILED,
                summary="",
                error=str(exc),
            )
        except Exception as exc:
            logger.error(
                "ResearchAgent: unexpected error",
                task_id=task.id,
                error=str(exc),
            )
            return TaskResult(
                task_id=task.id,
                agent_id=self.name,
                status=TaskStatus.FAILED,
                summary="",
                error=f"Unexpected error: {exc}",
            )

    def _build_messages(self, task: Task) -> List[Message]:
        """Constructs system and user Message objects for the LLM call."""
        system_prompt = (
            "You are a highly skilled Research Agent. "
            "Your task is to provide a clear, accurate, and well-structured response "
            "to the research query. Be concise yet comprehensive."
        )
        user_prompt = f"{task.description}\n\nQuery: {task.name}"

        return [
            Message(
                id=generate_uuid(),
                role=RoleEnum.SYSTEM,
                content=system_prompt,
            ),
            Message(
                id=generate_uuid(),
                role=RoleEnum.USER,
                content=user_prompt,
            ),
        ]

    async def shutdown(self) -> None:
        """Shutdown lifecycle hook."""
        logger.info("ResearchAgent: shutting down", agent=self.name)
