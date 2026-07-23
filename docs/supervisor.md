# Supervisor Architecture

The Supervisor in AgentOS is decomposed into dedicated single-responsibility components to avoid a monolithic orchestrator pattern.

## Components

- `orchestrator.py`: Top-level coordinator that sequences workflow execution across components.
- `planner.py`: `BaseSupervisorPlanner` interface for decomposing goals into atomic execution tasks.
- `router.py`: `BaseSupervisorRouter` interface for dynamically querying `AgentRegistry` and routing tasks.
- `scheduler.py`: `BaseSupervisorScheduler` interface for queuing and scheduling task execution sequences.
- `validator.py`: `BaseSupervisorValidator` interface for checking execution results against goal criteria.
- `report_generator.py`: `BaseSupervisorReportGenerator` interface for synthesizing multi-agent outputs into final responses.
- `memory_bridge.py`: `BaseSupervisorMemoryBridge` interface for interfacing supervisor state with layered memory stores.
