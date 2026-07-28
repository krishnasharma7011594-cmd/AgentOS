"""
Dependency Injection Container

Wires component dependencies for AgentOS at application startup.
Initializes registries, instantiates agents, configures LLM providers, and binds
the decomposed Supervisor subcomponents into a unified SupervisorOrchestrator.

Phase 4.5: Registers AgentMetadata alongside agents; passes CapabilityRegistry
to SupervisorValidator for plan-level capability checking.

Phase 7: Registers EmbeddingProvider, VectorMemoryProvider, DefaultKnowledgeRepository,
and MemoryService. Injects MemoryService into SupervisorOrchestrator.

Architecture Layer: Core / DI
"""

from core.ai.embeddings.deterministic import DeterministicEmbeddingProvider
from core.ai.providers.base import BaseLLMProvider
from core.ai.providers.factory import build_llm_provider
from core.config.settings import Settings
from core.config.settings import settings as _global_settings
from core.logging.logger import logger
from core.memory.providers.vector import VectorMemoryProvider
from core.memory.repository import DefaultKnowledgeRepository
from core.memory.service import MemoryService
from core.tools.implementations.web_search import WebSearchTool
from core.tools.registry import ToolRegistry
from registry.agent_registry import AgentRegistry
from registry.capability_registry import CapabilityRegistry
from supervisor.orchestrator import SupervisorOrchestrator
from supervisor.planner import SupervisorPlanner
from supervisor.report_generator import SupervisorReportGenerator
from supervisor.router import SupervisorRouter
from supervisor.validator import SupervisorValidator


def _register_agents(
    agent_registry: AgentRegistry,
    capability_registry: CapabilityRegistry,
    tool_registry: ToolRegistry,
    llm_provider: BaseLLMProvider,
) -> None:
    """
    Instantiates agents and registers them with their capabilities and metadata.

    Agents self-register their functional capabilities into CapabilityRegistry during
    startup. This enables dynamic routing: the Supervisor discovers agents by capability
    rather than importing agent modules directly.

    Phase 4.5: AgentRegistry.register_agent() auto-extracts METADATA from agent
    class variables — no extra registration step needed.
    """
    from agents.coding.agent import CodingAgent
    from agents.research.agent import ResearchAgent

    # ResearchAgent
    research_agent = ResearchAgent(
        llm_provider=llm_provider,
        tool_registry=tool_registry,
    )
    agent_registry.register_agent(research_agent.name, research_agent)
    capability_registry.register_agent_capabilities(
        research_agent.name,
        research_agent.capabilities,
    )
    logger.info(
        "DI: ResearchAgent registered",
        capabilities=[c.name for c in research_agent.capabilities],
    )

    # CodingAgent
    coding_agent = CodingAgent(
        llm_provider=llm_provider,
        tool_registry=tool_registry,
    )
    agent_registry.register_agent(coding_agent.name, coding_agent)
    capability_registry.register_agent_capabilities(
        coding_agent.name,
        coding_agent.capabilities,
    )
    logger.info(
        "DI: CodingAgent registered",
        capabilities=[c.name for c in coding_agent.capabilities],
    )

    # TODO: Register GitHubAgent and FinanceAgent as their implementations complete.


def build_orchestrator(app_settings: Settings | None = None) -> SupervisorOrchestrator:
    """
    Constructs and wires the complete AgentOS runtime component graph.

    Instantiates the configured LLM provider, registries, agents, and decomposed
    supervisor services (Planner, Router, Validator, ReportGenerator) before
    binding them into the SupervisorOrchestrator.

    Args:
        app_settings: Optional Settings object override.

    Returns:
        SupervisorOrchestrator: Fully wired orchestrator instance.
    """
    cfg = app_settings or _global_settings

    logger.info("DI: building AgentOS component graph")

    # 1. Build provider abstraction
    llm_provider = build_llm_provider(cfg)

    # 2. Initialize registries
    agent_registry = AgentRegistry()
    capability_registry = CapabilityRegistry()
    tool_registry = ToolRegistry()

    # Register default tools in global ToolRegistry
    tool_registry.register(WebSearchTool())

    # 3. Register active agents (auto-registers metadata from METADATA ClassVar)
    _register_agents(agent_registry, capability_registry, tool_registry, llm_provider)

    # 4. Instantiate supervisor subcomponents
    # Validator receives CapabilityRegistry for plan-level capability checking
    planner = SupervisorPlanner()
    router = SupervisorRouter(
        agent_registry=agent_registry,
        capability_registry=capability_registry,
    )
    validator = SupervisorValidator(capability_registry=capability_registry)
    report_generator = SupervisorReportGenerator()

    # 5. Memory subsystem (Phase 7)
    embedding_provider = DeterministicEmbeddingProvider()
    memory_provider = VectorMemoryProvider()
    knowledge_repository = DefaultKnowledgeRepository(provider=memory_provider)
    memory_service = MemoryService(
        repository=knowledge_repository,
        embedding_provider=embedding_provider,
    )
    logger.info("DI: MemoryService registered (VectorMemoryProvider + DeterministicEmbeddings)")

    # 6. Assemble orchestrator
    orchestrator = SupervisorOrchestrator(
        agent_registry=agent_registry,
        capability_registry=capability_registry,
        planner=planner,
        router=router,
        validator=validator,
        report_generator=report_generator,
        memory_service=memory_service,
    )

    logger.info(
        "DI: AgentOS component graph ready",
        provider=cfg.llm.default_provider,
        agents=agent_registry.list_agents(),
        capabilities=capability_registry.list_capabilities(),
        tools=[t.name for t in tool_registry.list_tools()],
    )
    return orchestrator
