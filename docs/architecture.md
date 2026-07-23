# AgentOS Architecture Overview

AgentOS is built as a production-grade modular Agentic AI Operating System following SOLID principles, Clean Architecture, and strict dependency boundaries.

## System Layering

1. **Apps Layer** (`apps/`): Serves end-user interfaces (FastAPI REST API, Typer CLI, Dashboard).
2. **Supervisor Layer** (`supervisor/`): Multi-agent orchestrator broken down into specialized responsibility components (`orchestrator`, `planner`, `router`, `scheduler`, `validator`, `report_generator`, `memory_bridge`).
3. **Registry Layer** (`registry/`): Dynamic runtime registration and capability indexing (`agent_registry`, `tool_registry`, `capability_registry`).
4. **Agents Layer** (`agents/`): Domain specialized autonomous agents (`research`, `coding`, `github`, `finance`) following a uniform module template.
5. **Workflow & Task Queue Layer** (`workflow/`, `task_queue/`): State machines (`Planning`, `Queued`, `Running`, `Waiting`, `Completed`, `Failed`, `Cancelled`) and background workers.
6. **Core Layer** (`core/`): Foundational AI providers (`core/ai/`), layered memory (`core/memory/`), tool runtime (`core/tools/`), communication bus (`core/communication/`), observability (`observability/`), and evaluation (`evaluation/`).
7. **Knowledge Layer** (`knowledge/`): Document ingestion, embedding providers, vectorstore interfaces, OKF, and retrieval indexers.

## Key Design Principles
- **No Direct Inter-Agent Dependencies**: Agents never import or invoke other agents.
- **Dynamic Discovery**: The Supervisor never hardcodes agent names; agents self-register via `AgentRegistry`.
- **Dependency Injection**: Dependencies are passed explicitly to constructors to maintain testability and clean architecture.
