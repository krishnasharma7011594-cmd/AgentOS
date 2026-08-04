# Supervisor Architecture

The Supervisor in AgentOS is decomposed into dedicated single-responsibility components to avoid a monolithic orchestrator pattern.

## Components

- `orchestrator.py`: Top-level coordinator that sequences workflow execution across components.
- `planner.py`: `BaseSupervisorPlanner` interface for decomposing goals into atomic execution tasks.
- `router.py`: `BaseSupervisorRouter` interface for dynamically querying `AgentRegistry` and routing tasks.
- `scheduler.py`: `BaseSupervisorScheduler` interface for queuing and scheduling task execution sequences.
- `validator.py`: `BaseSupervisorValidator` interface for checking execution results against goal criteria.
- `report_generator.py`: `BaseSupervisorReportGenerator` interface for synthesizing multi-agent outputs into final responses.
- `memory_bridge.py`: `SupervisorMemoryBridge` — concrete implementation of `BaseSupervisorMemoryBridge`. Persists goal context, execution results, and reflection reports to the layered `MemoryService` after each orchestration cycle. Used directly by `orchestrator.py` (refactored in Phase 10).
