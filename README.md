# AgentOS

> **Notice**: AgentOS is currently under active development.

## Why this exists
AgentOS is a production-grade, highly modular, clean-architecture framework designed to evolve into an Agentic AI Operating System. It provides a supervisor-driven, multi-agent runtime where tasks are dynamically planned, routed, validated, and executed using a robust DAG-based `ExecutionGraph`.

---

## 🌟 Architecture Overview

AgentOS strictly enforces **SOLID principles** and **Clean Architecture**. Dependencies flow unidirectionally downward.

### 1. Structural & Dependency Architecture
This diagram illustrates how the system's core components are decoupled through dependency injection, abstract interfaces, and registries.

```text
                  [ User / Client ]
                         │
                         ▼
                   [ Apps Layer ] (FastAPI / REST, Typer CLI, Dashboard)
                          │
                          ▼
              [ Supervisor Orchestrator ]
           [ ExecutionGraph & MetricsCollector ]
           [ DecisionEngine & ReflectionEngine ]┌─────────────┼─────────────┐
           ▼             ▼             ▼
      [ Planner ]   [ Router ]   [ Evaluator ]
                         │             │
                         │             ▼
                         │     [ DecisionEngine ]
                         │             │
                         ▼             ▼
               [ CapabilityRegistry ]  (Events)
                         │
                         ▼
                [ AgentRegistry ]
                         │  (Runtime Lookup: Agent Name → Instance)
                         ▼
                 [ ResearchAgent ]
                         │
                         ▼
               [ BaseLLMProvider ]
            ┌────────────┴────────────┐
            ▼                         ▼
    [ GeminiProvider ]        [ GroqProvider ]
```

### 2. Execution & Data Flow Lifecycle
This diagram details the chronological journey of a user request as it flows through the Supervisor, ExecutionGraph, and Agents.

```text
                         User
                          │
                          ▼
                     FastAPI API
                          │
                          ▼
                Supervisor Orchestrator
                          │
                          ▼
                 Supervisor Planner
                          │
                          ▼
                 Plan Validation
                          │
                          ▼
                  ExecutionGraph
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
   Research Agent                  Coding Agent
          │                               │
          ▼                               ▼
      ReAct Loop                     ReAct Loop
          │                               │
          ▼                               ▼
     Tool Registry                   Tool Registry
          │                               │
          ▼                               ▼
      Web Search                     Future Tools
          │                               │
          └───────────────┬───────────────┘
                          ▼
                  TaskEvaluator
                          ▼
                 DecisionEngine (Retry/Skip/Replan)
                          ▼
                  ExecutionContext & MetricsCollector
                          ▼
                   ReportBuilder
                          ▼
                   ExecutionResult
                          ▼
                         User
```

### Key Architectural Safeguards
1. **Zero Hardcoded Agent References**: The Supervisor never imports concrete agent modules or references agent names directly. It delegates tasks to `CapabilityRegistry`.
2. **Interchangeable LLM Providers**: Agents depend strictly on `BaseLLMProvider`. Providers (Gemini, Groq) are resolved at runtime via dependency injection.
3. **No Direct Inter-Agent Coupling**: Agents never import or invoke other agents directly.

---

## 🚀 Module Status Inventory

| Module / Directory | Status | Description / Notes |
| :--- | :--- | :--- |
| `core/` | **Implemented** | Core foundational types, AI providers, tools, dependency injection, and layered memory. |
| `supervisor/` | **Implemented** | Highly developed orchestrator, adaptive execution graph, decision engine, and plan evaluation. |
| `registry/` | **Implemented** | Contains the `AgentRegistry` and `CapabilityRegistry` (recently refactored for the Capability framework). |
| `apps/api/` | **Implemented** | FastAPI application layer, endpoints, and server lifecycle logic. |
| `apps/cli/` | **Partial** | Basic CLI entrypoint (`typer` wrapper) but lacks advanced operational commands. |
| `apps/dashboard/` | **Interface-only** | 10-line placeholder file (`app.py`); no UI implemented yet. |
| `agents/` | **Implemented** | Contains four fully implemented domain agents with specific tool access and system prompts: `research` (271 lines), `coding` (178 lines), `finance` (109 lines), and `github` (103 lines). |
| `knowledge/` | **Interface-only** | Skeletons and abstract base classes for VectorDB / Document ingestion (`base.py`, `okf/`, etc). |
| `observability/` | **Interface-only** | Skeleton files (`tracing.py`, `metrics.py`) containing `NotImplementedError` stubs for future telemetry. |
| `evaluation/` | **Interface-only** | Stubs (`judge.py`, `benchmarks.py`) for future LLM-as-a-judge capabilities. |
| `workflow/` | **Interface-only** | Empty or placeholder logic for future state-machine based workflows. |
| `task_queue/` | **Interface-only** | Stubs for asynchronous worker queues (`worker.py`, `queue.py`). |

---

## 🏗️ Design Decisions

AgentOS is built upon several rigorous architectural decisions designed to ensure scalability and decoupling:

1. **DAG Execution vs. Sequential Loops**: 
   Instead of a traditional `while True` loop, AgentOS maps tasks into a Directed Acyclic Graph (`ExecutionGraph`). This enables native parallel execution of independent tasks, dependency cascade skips, and dynamic graph mutation (replanning) without losing global state.
2. **Capability-Registry Routing vs. Hardcoded Refs**:
   The Supervisor does not know about the `ResearchAgent` or `CodingAgent`. Instead, it resolves tasks dynamically via the `CapabilityRegistry`. Tasks declare a `required_capability`, and the registry binds them to the correct agent/tool at runtime.
3. **Provider Abstraction vs. Direct SDK Calls**:
   Agents never directly import `google.generativeai` or `groq`. All AI capabilities are funneled through a strict `BaseLLMProvider` interface, allowing the entire model backend to be swapped out instantaneously via dependency injection.
4. **Tool Sandboxing Limitations (Caveat)**:
   While the architecture defines a distinct `ToolSandbox` to capture exceptions and enforce `asyncio` timeouts, **tools currently execute in the same Python process as the orchestrator**. There is no Docker/gVisor isolation or strict OS-level permission enforcement implemented yet.

---

## 🛠️ Tech Stack

- **Core Logic & Runtime**: Python 3.11+
- **REST API**: FastAPI & Uvicorn
- **Configuration & Validation**: Pydantic v2 & Pydantic Settings
- **Structured Logging**: Structlog
- **LLM Integrations**: `google-generativeai`, `groq`
- **CLI**: Typer
- **Dev Tooling & Quality**: Pytest, Ruff, Black, Mypy, Pre-Commit
- **Containerization & CI**: Docker, Docker Compose, GitHub Actions

---

## 📋 Project Structure

```text
AgentOS/
├── apps/                 # User-facing application layers
│   ├── api/              # REST endpoint routers (/chat, /task, /health, /agents)
│   ├── cli/              # Terminal CLI application
│   └── dashboard/        # Web dashboard UI (Placeholder)
├── supervisor/           # Orchestrator, planner, router, validator, decision_handler, reflection
├── registry/             # Runtime discovery registries (agent_registry, capability_registry)
├── agents/               # Autonomous agents (research, coding, github, finance)
├── core/                 # Core infrastructure
│   ├── ai/               # Provider abstractions & implementations (Gemini, Groq)
│   ├── communication/    # Inter-agent messaging structures
│   ├── config/           # Pydantic Settings configuration loader
│   ├── context/          # Context engine and state bounds
│   ├── di/               # Dependency injection container
│   ├── exceptions/       # Custom domain exception hierarchy
│   ├── execution/        # Graph execution engine, events, and metrics
│   ├── logging/          # Centralized structured logger
│   ├── memory/           # Multi-tiered memory layers (working, session, long-term)
│   ├── models/           # Domain entities (Goal, Task, TaskResult, ExecutionResult)
│   ├── parallel/         # Dependency resolution and parallel execution engine
│   ├── prompts/          # System prompts and templates
│   ├── security/         # Security and sanitization protocols
│   ├── tools/            # Capability Executor, Engine, Sandbox, and Implementations
│   ├── utils/            # General utilities
│   └── validators/       # Input/Output validation layers
├── knowledge/            # RAG contracts (documents, embeddings, retrievers, vectorstores)
├── workflow/             # State machine states & transitions
├── task_queue/           # Abstract task queue & worker interfaces
├── observability/        # Tracing, metrics, and performance interfaces
├── evaluation/           # Benchmarks & evaluation metrics interfaces
├── docs/                 # Architectural documentation
├── docker/               # Container configurations (Dockerfile, docker-compose.yml)
├── tests/                # Pytest test suite
├── .env.example          # Environment variables template
├── pyproject.toml        # Project dependencies & tool configurations
└── README.md
```

---

## 💻 Quick Start

### 1. Prerequisites
- Python 3.11 or higher
- Git

### 2. Clone and Setup Environment
```bash
git clone https://github.com/krishnasharma7011594-cmd/AgentOS.git
cd AgentOS
cp .env.example .env
```

Edit `.env` to configure your API keys:
```env
DEFAULT_LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Install Dependencies
```bash
pip install -e .[dev]
```

### 4. Run Development Server
```bash
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive API documentation will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

### 5. Send Test Request
```bash
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Explain what LangGraph is."}'
```

---

## 🗺️ Current Roadmap

### Phase 1: Architecture & Infrastructure Skeleton
**Status:** **Done**
- Monorepo directory structure setup.
- Core ABC interfaces (`BaseAgent`, `BaseTool`, `BaseMemory`, `BaseLLMProvider`, `BasePlanner`).
- Pydantic Settings & Domain Models.
- Docker & CI/CD pipeline setup (ruff, black, mypy, pytest).

### Phase 2: Core Runtime Implementation
**Status:** **Done**
- Real LLM integrations (Gemini via `google-generativeai`, Groq via `groq` SDK).
- Agent & Capability Registries (in-memory registration).
- `apps/api/` FastAPI layer (`POST /chat`, `POST /task`, etc).
- `apps/cli/` basic terminal application.

### Phase 3: Basic Orchestration
**Status:** **Done**
- Decomposed Supervisor module (Planner, Router, Evaluator, ReportGenerator).
- Execution pipelines and basic Task scheduling.

### Phase 4: Execution State Machine
**Status:** **Done**
- Implementation of the `ExecutionGraph`.
- Replaced linear task loop with state-machine task progression (READY, RUNNING, COMPLETED, FAILED, SKIPPED).

### Phase 5: Adaptive Supervisor
**Status:** **Done**
- Integration of `TaskEvaluator` for structured evaluation.
- `DecisionEngine` implementation for branching (CONTINUE, RETRY, SKIP, REPLAN, TERMINATE).
- Mutating graph structures mid-execution based on failure context.

### Phase 6: Reflective Processing
**Status:** **Done**
- `ReflectionEngine` implemented to analyze execution traces and produce `ReflectionReport`.
- Quantitative scoring of outcomes vs goals.

### Phase 7: Memory & Knowledge Subsystem
**Status:** **Partial**
- **Layered Memory (`core/memory/`):** **Done** (MemoryService and providers to store Executions and Reflections).
- **Knowledge/Vector DB (`knowledge/`):** **Not Started** (Only interface stubs exist).

### Phase 8: Telemetry & Observability
**Status:** **Not Started**
- The `observability/` module only contains Interface stubs (`tracing.py`, `metrics.py` throw `NotImplementedError`). OpenTelemetry tracking is pending.

### Phase 9: Parallel Execution & Dependency Resolution
**Status:** **Done**
- `ExecutionDependencyResolver` and `ParallelExecutionEngine` implemented.
- `orchestrator.py` dynamically dispatches independent tasks asynchronously.

### Phase 10: Capability-Driven System Integration (Current Phase)
**Status:** **In Progress**
- **Architecture split (CapabilityResolver, CapabilityEngine, CapabilityExecutor):** **Done**.
- **Dynamic Tool Sandboxing (`ToolSandbox`):** **Partial** (Executes in-process with `asyncio` timeouts, but lacks hard security constraints/Docker isolation).

### Phase 11: Production Deployment & Scaling
**Status:** **Not Started**
- **Asynchronous Task Queue (`task_queue/`):** **Not Started** (Only interface stubs).
- **Web Dashboard UI (`apps/dashboard/`):** **Not Started** (Empty placeholder script).
- **Workflow State Machines (`workflow/`):** **Not Started** (Interface stubs).

---

## 🧪 Testing & Quality Standards

Run the full verification suite locally:
```bash
# Run unit & integration tests
pytest

# Check code formatting
black --check .

# Run linter
ruff check .

# Run static type checker
mypy .
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:
1. Review the [Architecture Documentation](docs/architecture.md) and [Contributing Guide](docs/contributing.md).
2. Create a feature branch (`git checkout -b feature/amazing-feature`).
3. Ensure all tests and linting pass (`pytest && ruff check . && black --check .`).
4. Open a Pull Request.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
