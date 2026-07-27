# AgentOS

> **Notice**: AgentOS is currently under active development. Phases 1 through 4.5 are complete.

AgentOS is a production-grade, highly modular, clean-architecture framework designed to evolve into an Agentic AI Operating System. It provides a supervisor-driven, multi-agent runtime where tasks are dynamically planned, routed, validated, and executed using a robust DAG-based `ExecutionGraph`.

---

## 🌟 Architecture Overview

AgentOS strictly enforces **SOLID principles** and **Clean Architecture**. Dependencies flow unidirectionally downward:

```
                  [ User / Client ]
                         │
                         ▼
                   [ Apps Layer ] (FastAPI / REST, Typer CLI, Dashboard)
                          │
                          ▼
              [ Supervisor Orchestrator ]
           (ExecutionGraph & MetricsCollector)
           ┌─────────────┼─────────────┐
           ▼             ▼             ▼
      [ Planner ]   [ Router ]   [ Validator ]
                         │
                         ▼
               [ CapabilityRegistry ]
                         │  (Dynamic Resolution: Capability → Agent Name)
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

### Key Architectural Safeguards
1. **Zero Hardcoded Agent References**: The Supervisor never imports concrete agent modules or references agent names directly. It delegates tasks to `CapabilityRegistry`.
2. **Interchangeable LLM Providers**: Agents depend strictly on `BaseLLMProvider`. Providers (Gemini, Groq) are resolved at runtime via dependency injection.
3. **No Direct Inter-Agent Coupling**: Agents never import or invoke other agents directly.

---

## 🚀 Features Implemented (Up to Phase 4.5)

- **Decomposed Supervisor Architecture**: Separated single-responsibility services (`orchestrator`, `planner`, `router`, `validator`, `report_generator`).
- **Graph-based Execution Engine**: Replaced sequential loops with `ExecutionGraph` (DAG state machine) that handles dynamic task skipping, dependencies, and execution states.
- **Telemetry & Reporting**: Embedded `MetricsCollector` to track agent runtime and logic step counts. Uses `ReportBuilder` to synthesize structured `ExecutionReport`s.
- **Dynamic Registries**: `AgentRegistry` and `CapabilityRegistry` support metadata-driven lookup and capability prioritization for runtime resolution.
- **Provider Abstraction & Factory**: `BaseLLMProvider` interface with operational `GeminiProvider` (`gemini-1.5-flash`) and `GroqProvider` (`llama-3.3-70b-versatile`).
- **Standardized Modules**: Uniform structure across agents (`ResearchAgent`, `CodingAgent`, etc.) utilizing declarative `METADATA` classes (`AgentMetadata` and `ToolMetadata`).
- **FastAPI Endpoint Suite**: Full REST endpoints (`POST /chat`, `POST /task`, `GET /health`, `GET /agents`).
- **Structured Logging & Diagnostics**: Production JSON logging via `structlog`.
- **Developer & DevOps Suite**: Pytest suite, Ruff linting, Black formatting, Mypy type-checking, Docker build, and GitHub Actions CI pipeline.

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

```
AgentOS/
├── apps/                 # User-facing application layers (api, cli, dashboard)
│   └── api/
│       └── routers/      # REST endpoint routers (/chat, /task, /health, /agents)
├── supervisor/           # Supervisor services (orchestrator, planner, router, validator, report_generator)
├── registry/             # Runtime discovery registries (agent_registry, capability_registry)
├── agents/               # Autonomous agents (research, coding, github, finance)
├── core/                 # Core infrastructure
│   ├── ai/               # Provider abstractions & implementations (Gemini, Groq, OpenAI)
│   ├── config/           # Pydantic Settings configuration loader
│   ├── di/               # Dependency injection container
│   ├── exceptions/       # Custom domain exception hierarchy
│   ├── execution/        # Graph execution engine, context, metrics, and reporting
│   ├── logging/          # Centralized structured logger
│   ├── memory/           # Multi-tiered memory layers (working, session, long-term, cache)
│   ├── models/           # Domain entities (Goal, Task, TaskResult, ExecutionResult, ExecutionReport)
│   └── tools/            # BaseTool & ToolRegistry interfaces
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
git clone https://github.com/your-org/AgentOS.git
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
# OR using poetry:
poetry install
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

## 🗺️ Current Roadmap

- [x] **Phase 1: Architecture & Monorepo Skeleton** — SOLID design, ABCs, registry, and dependency injection container.
- [x] **Phase 2: Functional End-to-End Orchestration** — Full `POST /chat` → `Supervisor` flow.
- [x] **Phase 3 & 4: Tools & Agents** — Basic tool execution and multi-agent integrations.
- [x] **Phase 4.5: Architecture Refinement** — Graph-based execution engine (`ExecutionGraph`), DAG plan validation, telemetry/metrics, and metadata-driven capability routing.
- [ ] **Phase 5: Advanced Planning & RAG** — Dynamic replanning, RAG memory persistence, and web dashboard.

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
