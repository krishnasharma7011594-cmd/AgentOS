# Phase 5 Design
## Adaptive Supervisor

Status: Design
Version: 1.0

---

# Objective

Phase 5 transforms the Supervisor from a workflow executor into an adaptive orchestrator.

Until Phase 4.5, the Supervisor executes a static execution graph generated before execution begins.

Beginning with Phase 5, the Supervisor will continuously evaluate execution progress, react to failures, modify plans when necessary, and make runtime decisions.

The Supervisor becomes an active decision-maker rather than a passive coordinator.

---

# Current Architecture

Current flow:

User
↓

Planner

↓

ExecutionGraph

↓

Execute

↓

Finish

The execution graph is static.

No changes occur after execution begins.

---

# Target Architecture

User

↓

Planner

↓

ExecutionGraph

↓

Execute Task

↓

Evaluate

↓

Decision Engine

↓

Continue
Retry
Replan
Skip
Finish

↓

Next Task

The execution graph becomes adaptive.

---

# Supervisor Responsibilities

The Supervisor is responsible for:

- planning
- validating
- scheduling
- monitoring execution
- evaluating task outcomes
- updating execution state
- determining next actions

The Supervisor is NOT responsible for:

- generating code
- performing research
- browsing
- executing tools
- making LLM responses directly

---

# Decision Engine

Every completed task is evaluated.

Pseudo flow:

Task Finished

↓

Evaluate Result

↓

Is task successful?

↓

Yes

↓

Continue

OR

↓

No

↓

Retry?

↓

No

↓

Replan?

↓

No

↓

Skip?

↓

Finish

The Supervisor becomes event-driven.

---

# Runtime Decisions

The Supervisor may decide to:

Continue execution

Retry a task

Skip a task

Generate additional tasks

Replace an agent

Terminate execution

Return partial results

Each decision must be explainable.

---

# Task Evaluation

Every TaskResult should answer:

Did the task succeed?

Did it partially succeed?

Can downstream tasks continue?

Is additional information required?

Should another capability be invoked?

---

# Failure Categories

Failures should be classified.

Examples:

Tool failure

LLM failure

Validation failure

Dependency failure

Timeout

Capability unavailable

User error

Unknown

Different failures require different decisions.

---

# Retry Strategy

Not every failure deserves a retry.

Example:

Timeout

↓

Retry

Capability missing

↓

Do not retry

Validation error

↓

Possibly replan

Maximum retry count should exist.

---

# Dynamic Replanning

The Supervisor may create new tasks during execution.

Example:

Research task discovers:

Need API documentation.

Supervisor inserts:

Documentation Lookup

before

Code Generation

ExecutionGraph grows dynamically.

---

# Agent Selection

Instead of always selecting the same agent:

Capability:

code_generation

↓

Available Agents

↓

Choose highest priority

↓

Execute

Future versions may include health scoring.

---

# Execution Events

Execution should become event-driven.

Examples:

TaskStarted

TaskCompleted

TaskFailed

TaskSkipped

TaskRetried

TaskInserted

ExecutionCompleted

Future systems may subscribe to these events.

---

# Reflection (Future)

Not implemented in Phase 5.

Possible future questions:

Was the chosen plan efficient?

Could fewer tasks solve the goal?

Was another agent a better choice?

Reflection is intentionally postponed.

---

# Parallel Execution

Not implemented.

ExecutionGraph already supports future DAG execution.

Parallel scheduling will be introduced later.

---

# Human Approval

Not implemented.

Future capability:

Pause execution

↓

Ask user

↓

Resume

---

# Memory

ExecutionContext remains request-scoped.

Persistent memory is introduced in later phases.

---

# Success Criteria

Phase 5 is complete when the Supervisor can:

- monitor execution
- evaluate outcomes
- retry appropriate failures
- skip impossible tasks
- dynamically insert new tasks
- continue execution without rebuilding the entire graph

while remaining independent of individual agents.

---

# Out of Scope

Phase 5 will NOT include:

- RAG
- Long-term memory
- Browser automation
- GitHub workflows
- Finance workflows
- Voice
- Parallel execution
- Reflection
- Human approval
