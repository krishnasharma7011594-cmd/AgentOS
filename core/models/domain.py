"""
Core Domain Models

Defines the foundational domain entities and data schemas for AgentOS using Pydantic.
Ensures strong typing, serialization, and schema validation across all application layers.

Phase 3 adds ReAct lifecycle models: ToolCall, ToolResult, Observation, ReasoningStep.
Phase 4 adds ExecutionContext and multi-task dependency support.
Phase 4.5 adds:
  - Expanded TaskStatus (READY, SKIPPED)
  - Capability (replaces AgentCapability) with version and priority
  - AgentMetadata and ToolMetadata for metadata-driven registries
  - ExecutionMetrics for structured telemetry
  - ExecutionReport as rich internal report model
  - PlanValidationResult for plan-level validation

Architecture Layer: Core / Models
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from core.utils.helpers import generate_uuid


class RoleEnum(str, Enum):
    """Message sender role enumeration."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    AGENT = "agent"
    TOOL = "tool"


class TaskStatus(str, Enum):
    """
    Lifecycle status for a Task across the workflow pipeline.

    State machine:
        PENDING → READY  (when all dependencies are satisfied)
        READY   → RUNNING (when the orchestrator picks up the task)
        RUNNING → SUCCESS | FAILED
        PENDING | READY → SKIPPED (when a dependency has failed)
    """

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Capability — replaces AgentCapability
# ---------------------------------------------------------------------------


class Capability(BaseModel):
    """
    Metadata contract defining a specific functional capability provided by an Agent.

    Replaces the former AgentCapability model. Adds version and priority for
    metadata-driven routing and capability resolution.

    Attributes:
        name:        Canonical capability key (e.g. 'web_research').
        description: Description of the capability for router discovery.
        version:     Semantic version of the capability implementation.
        priority:    Resolution priority — higher value wins when multiple agents
                     provide the same capability (default 0).
        parameters:  Expected input parameter schema (optional).
    """

    name: str = Field(..., description="Capability name")
    description: str = Field(..., description="What the capability provides")
    version: str = Field(default="1.0", description="Capability version")
    priority: int = Field(
        default=0,
        description="Resolution priority; higher wins ties",
    )
    parameters: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# AgentMetadata
# ---------------------------------------------------------------------------


class AgentMetadata(BaseModel):
    """
    Rich metadata descriptor for an AgentOS agent.

    Registered in AgentRegistry alongside the agent instance.
    Allows the Supervisor and observability tooling to inspect agent
    properties without coupling to implementation classes.

    Attributes:
        name:            Canonical agent name matching BaseAgent.name.
        description:     Human-readable role summary.
        version:         Semantic version of the agent implementation.
        author:          Owning team or developer name.
        capabilities:    List of Capability descriptors the agent exposes.
        supported_tools: Names of tools the agent may use at runtime.
    """

    name: str = Field(..., description="Canonical agent name")
    description: str = Field(..., description="Agent role summary")
    version: str = Field(default="1.0", description="Agent version")
    author: str = Field(default="AgentOS", description="Author or team name")
    capabilities: List[Capability] = Field(default_factory=list)
    supported_tools: List[str] = Field(
        default_factory=list,
        description="Tool names this agent may use",
    )


# ---------------------------------------------------------------------------
# ToolMetadata
# ---------------------------------------------------------------------------


class ToolMetadata(BaseModel):
    """
    Rich metadata descriptor for an AgentOS tool.

    Every tool exposes a class-level METADATA object so ToolRegistry can
    become metadata-driven instead of relying on implementation details.

    Attributes:
        name:          Canonical tool name matching BaseTool.name.
        description:   Human-readable capability summary.
        version:       Semantic version of the tool implementation.
        author:        Owning team or developer name.
        permissions:   Required runtime permissions (e.g. 'network', 'filesystem').
        tags:          Categorisation labels (e.g. ['search', 'web']).
        input_schema:  JSON schema describing accepted parameters.
        output_schema: JSON schema describing returned output structure.
    """

    name: str = Field(..., description="Canonical tool name")
    description: str = Field(..., description="Tool capability summary")
    version: str = Field(default="1.0", description="Tool version")
    author: str = Field(default="AgentOS", description="Author or team name")
    permissions: List[str] = Field(
        default_factory=list,
        description="Runtime permissions required (e.g. 'network')",
    )
    tags: List[str] = Field(default_factory=list, description="Categorisation labels")
    input_schema: Dict[str, Any] = Field(
        default_factory=dict,
        description="JSON schema of accepted input parameters",
    )
    output_schema: Dict[str, Any] = Field(
        default_factory=dict,
        description="JSON schema of produced output",
    )


# ---------------------------------------------------------------------------
# Core entities
# ---------------------------------------------------------------------------


class Message(BaseModel):
    """
    Standard message envelope transferred across agents, providers, and memory.

    Attributes:
        id:        Unique identifier for tracking.
        role:      Sender classification (user, system, assistant, agent, tool).
        content:   Text content of the message.
        metadata:  Arbitrary operational context metadata.
        timestamp: Time of message creation.
    """

    id: str = Field(default_factory=generate_uuid)
    role: RoleEnum = Field(..., description="Role of the sender")
    content: str = Field(..., description="Textual content of the message")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Goal(BaseModel):
    """
    Top-level user objective submitted to the Supervisor.

    Attributes:
        id:          Goal identifier.
        description: User prompt or high-level problem statement.
        constraints: Optional operational boundaries or requirements.
        created_at:  Objective timestamp.
    """

    id: str = Field(default_factory=generate_uuid)
    description: str = Field(..., description="Clear text description of the goal")
    constraints: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Task(BaseModel):
    """
    Atomic unit of work decomposed from a Goal by the Supervisor Planner.

    Attributes:
        id:                   Unique task identifier.
        goal_id:              Reference to parent Goal.
        assigned_agent_id:    Agent instance assigned to execute (resolved at routing).
        name:                 Short task title.
        description:          Detailed execution instructions for the agent.
        required_capability:  Capability key used by SupervisorRouter to match an agent.
        priority:             Priority ordering hint.
        status:               Execution lifecycle state (TaskStatus enum).
        dependencies:         List of task IDs that must succeed before this task runs.
        created_at:           Task creation timestamp.
    """

    id: str = Field(default_factory=generate_uuid)
    goal_id: str = Field(..., description="Associated parent Goal ID")
    assigned_agent_id: Optional[str] = Field(default=None)
    name: str = Field(..., description="Task title")
    description: str = Field(..., description="Detailed task requirements")
    required_capability: str = Field(..., description="Capability required to execute this task")
    priority: str = Field(default="medium", description="Task priority: high / medium / low")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of task IDs this task depends on",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExecutionPlan(BaseModel):
    """
    Ordered sequence of Tasks constructed by the Supervisor Planner to fulfill a Goal.

    Attributes:
        id:         Unique plan identifier.
        goal_id:    Parent Goal reference.
        tasks:      Sequenced list of Tasks to be executed.
        created_at: Plan creation timestamp.
    """

    id: str = Field(default_factory=generate_uuid)
    goal_id: str = Field(..., description="Target Goal ID")
    tasks: List[Task] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskResult(BaseModel):
    """
    Structured outcome returned by an Agent after processing a Task.

    Attributes:
        task_id:      Associated Task ID.
        agent_id:     Identifier of the executing agent.
        status:       Task execution outcome (TaskStatus enum).
        summary:      Output content produced by the agent.
        metadata:     Execution metrics and telemetry.
        error:        Error details if execution failed.
        completed_at: Completion timestamp.
    """

    task_id: str = Field(..., description="Associated Task ID")
    agent_id: str = Field(..., description="Agent that executed the task")
    status: TaskStatus = Field(..., description="Execution outcome status")
    summary: str = Field(..., description="Human-readable summary of the result")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = Field(default=None, description="Error message if failed")
    completed_at: datetime = Field(default_factory=datetime.utcnow)


class ExecutionContext(BaseModel):
    """
    Lightweight execution context passed between tasks during goal execution.

    Stores intermediate results to enable multi-agent collaboration where
    downstream agents can read the outputs of upstream tasks.

    Attributes:
        goal_id: Parent Goal ID.
        results: Dictionary mapping task IDs to their TaskResult.
    """

    goal_id: str = Field(..., description="Associated parent Goal ID")
    results: Dict[str, TaskResult] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Validation models
# ---------------------------------------------------------------------------


class ValidationResult(BaseModel):
    """
    Outcome of SupervisorValidator evaluation on a single TaskResult.

    Attributes:
        task_id:      Evaluated Task ID.
        is_valid:     Boolean status of the validation check.
        reason:       Explanatory validation notes.
        validated_at: Timestamp of the validation check.
    """

    task_id: str
    is_valid: bool
    reason: str
    validated_at: datetime = Field(default_factory=datetime.utcnow)


class PlanValidationResult(BaseModel):
    """
    Outcome of SupervisorValidator evaluation on an ExecutionPlan.

    Attributes:
        is_valid: True only when all validation checks passed.
        errors:   List of human-readable validation error messages.
    """

    is_valid: bool
    errors: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Execution Metrics
# ---------------------------------------------------------------------------


class ExecutionMetrics(BaseModel):
    """
    Aggregate telemetry captured during one goal execution lifecycle.

    Attributes:
        total_tasks:           Total number of tasks in the plan.
        completed_tasks:       Tasks that reached SUCCESS status.
        failed_tasks:          Tasks that reached FAILED status.
        skipped_tasks:         Tasks that were SKIPPED due to dep failure.
        execution_time_ms:     Total wall-clock time in milliseconds.
        agent_execution_times: Per-agent cumulative execution time (ms).
        total_tool_calls:      Aggregate tool invocations across all tasks.
        total_reasoning_steps: Aggregate ReAct reasoning steps across all tasks.
    """

    total_tasks: int = Field(default=0)
    completed_tasks: int = Field(default=0)
    failed_tasks: int = Field(default=0)
    skipped_tasks: int = Field(default=0)
    execution_time_ms: float = Field(default=0.0)
    agent_execution_times: Dict[str, float] = Field(default_factory=dict)
    total_tool_calls: int = Field(default=0)
    total_reasoning_steps: int = Field(default=0)


# ---------------------------------------------------------------------------
# Execution Report (rich internal model)
# ---------------------------------------------------------------------------


class ExecutionReport(BaseModel):
    """
    Rich, structured execution report produced after a goal lifecycle completes.

    This is the internal model surfaced through ExecutionResult.report.
    It provides structured sections for observability, debugging, and future UI.

    Attributes:
        goal_id:             Parent Goal ID.
        goal_description:    Original goal text.
        overall_status:      'success' | 'partial' | 'failed'.
        completed_tasks:     TaskResult list for SUCCESS tasks.
        skipped_tasks:       TaskResult list for SKIPPED tasks.
        failed_tasks:        TaskResult list for FAILED tasks.
        agent_contributions: Agent name → list of task summaries they produced.
        metrics:             Aggregate ExecutionMetrics.
        final_response:      Synthesized text returned to API callers.
        generated_at:        Report generation timestamp.
    """

    goal_id: str = Field(..., description="Parent Goal ID")
    goal_description: str = Field(..., description="Original goal text")
    overall_status: str = Field(..., description="success | partial | failed")
    completed_tasks: List[TaskResult] = Field(default_factory=list)
    skipped_tasks: List[TaskResult] = Field(default_factory=list)
    failed_tasks: List[TaskResult] = Field(default_factory=list)
    agent_contributions: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="agent_id → list of task summaries",
    )
    metrics: ExecutionMetrics = Field(default_factory=ExecutionMetrics)
    final_response: str = Field(..., description="Synthesized final answer text")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# ExecutionResult — public API surface (backward compatible)
# ---------------------------------------------------------------------------


class ExecutionResult(BaseModel):
    """
    Final aggregated response produced by SupervisorReportGenerator and returned to caller.

    Backward compatible with Phase 4. The optional `report` field exposes the
    rich ExecutionReport for consumers that need structured execution data.

    Attributes:
        goal_id:   Parent Goal ID.
        status:    Overall orchestration status (success, partial, failed).
        response:  Final synthesized text payload.
        tasks:     List of individual TaskResult records.
        report:    Optional rich ExecutionReport for structured consumption.
    """

    goal_id: str
    status: str = Field(..., description="overall: success | partial | failed")
    response: str = Field(..., description="Synthesized final response text")
    tasks: List[TaskResult] = Field(default_factory=list)
    report: Optional[ExecutionReport] = Field(
        default=None,
        description="Rich structured execution report (Phase 4.5+)",
    )
    completed_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Phase 3 — ReAct Lifecycle Models
# ---------------------------------------------------------------------------
# These four models represent one complete iteration of the ReAct loop:
#   ToolCall → agent decides WHAT to call and with WHAT parameters.
#   ToolResult → raw output returned by the tool after execution.
#   Observation → agent's contextual interpretation of a ToolResult.
#   ReasoningStep → one complete Think → Act → Observe record.
#
# Keeping them in domain.py means every layer (agents, supervisor, observability)
# can import them without creating circular dependencies.
# ---------------------------------------------------------------------------


class ToolCall(BaseModel):
    """
    Represents the agent's intent to invoke a tool.

    Generated during the 'Act' phase of the ReAct loop after the LLM has
    selected a tool and constructed its input parameters.

    Attributes:
        call_id:    Unique ID for correlating calls with results.
        tool_name:  Registry name of the tool to invoke.
        parameters: Key-value arguments to pass to the tool.
    """

    call_id: str = Field(default_factory=generate_uuid)
    tool_name: str = Field(..., description="Name of the tool to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """
    Raw output returned by a tool after execution.

    Produced by ToolRegistry.execute() and passed back to the ReAct loop
    to be wrapped into an Observation.

    Attributes:
        call_id:   Correlates to the originating ToolCall.
        tool_name: Name of the tool that produced this result.
        output:    String representation of the tool's output.
        error:     Non-None when execution raised an exception.
        success:   False when tool raised an error.
    """

    call_id: str = Field(..., description="Matches originating ToolCall.call_id")
    tool_name: str = Field(..., description="Name of the tool that ran")
    output: str = Field(..., description="String output from tool execution")
    error: Optional[str] = Field(default=None, description="Error message on failure")
    success: bool = Field(default=True, description="False when execution failed")


class Observation(BaseModel):
    """
    The agent's contextual record of a tool execution result.

    Inserted into the ReAct prompt history so subsequent reasoning steps
    can reference what the tool returned.

    Attributes:
        step:        Index of the reasoning loop iteration (1-based).
        tool_result: Underlying ToolResult from the registry.
        content:     Human-readable summary injected into the next prompt.
    """

    step: int = Field(..., description="Reasoning loop iteration (1-based)")
    tool_result: ToolResult
    content: str = Field(..., description="Observation text injected into next reasoning prompt")


class ReasoningStep(BaseModel):
    """
    A complete record of one ReAct iteration: Thought → Action → Observation.

    ReasoningSteps are accumulated in a list throughout the agent lifecycle
    and surfaced in TaskResult.metadata for full traceability.

    Attributes:
        step:         1-based iteration index.
        thought:      LLM's internal reasoning text.
        action:       Name of the chosen tool (None if final answer step).
        action_input: Parameters passed to the tool.
        observation:  Tool result summary (None on final answer steps).
        is_final:     True when the LLM produced a Final Answer instead of an action.
        final_answer: Populated only when is_final=True.
    """

    step: int = Field(..., description="Iteration index (1-based)")
    thought: str = Field(..., description="LLM reasoning text for this step")
    action: Optional[str] = Field(default=None, description="Tool name selected, if any")
    action_input: Optional[Dict[str, Any]] = Field(default=None)
    observation: Optional[str] = Field(default=None, description="Observation from tool result")
    is_final: bool = Field(default=False, description="True when this step produces the answer")
    final_answer: Optional[str] = Field(default=None, description="Answer text when is_final=True")
