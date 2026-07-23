"""
Core Domain Models

Defines the foundational domain entities and data schemas for AgentOS using Pydantic.
Ensures strong typing, serialization, and schema validation across all application layers.

Phase 3 adds ReAct lifecycle models: ToolCall, ToolResult, Observation, ReasoningStep.
These are shared across all agents so the same reasoning primitives work for Research,
Coding, GitHub, Finance, and any future agent.

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
    """Lifecycle status for a Task across the workflow pipeline."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class Message(BaseModel):
    """
    Standard message envelope transferred across agents, providers, and memory.

    Attributes:
        id: Unique identifier for tracking.
        role: Sender classification (user, system, assistant, agent, tool).
        content: Text content of the message.
        metadata: Arbitrary operational context metadata.
        timestamp: Time of message creation.
    """

    id: str = Field(default_factory=generate_uuid)
    role: RoleEnum = Field(..., description="Role of the sender")
    content: str = Field(..., description="Textual content of the message")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentCapability(BaseModel):
    """
    Metadata contract defining a specific functional capability provided by an Agent.

    Attributes:
        name: Canonical capability key (e.g. 'web_research').
        description: Description of the capability for router discovery.
        parameters: Expected input parameter schema.
    """

    name: str = Field(..., description="Capability name")
    description: str = Field(..., description="What the capability provides")
    parameters: Dict[str, Any] = Field(default_factory=dict)


class Goal(BaseModel):
    """
    Top-level user objective submitted to the Supervisor.

    Attributes:
        id: Goal identifier.
        description: User prompt or high-level problem statement.
        constraints: Optional operational boundaries or requirements.
        created_at: Objective timestamp.
    """

    id: str = Field(default_factory=generate_uuid)
    description: str = Field(..., description="Clear text description of the goal")
    constraints: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Task(BaseModel):
    """
    Atomic unit of work decomposed from a Goal by the Supervisor Planner.

    Attributes:
        id: Unique task identifier.
        goal_id: Reference to parent Goal.
        assigned_agent_id: Agent instance assigned to execute this task (resolved at routing).
        name: Short task title.
        description: Detailed execution instructions for the agent.
        required_capability: Key used by SupervisorRouter to discover a matching agent.
        priority: Priority ordering hint.
        status: Execution lifecycle state.
    """

    id: str = Field(default_factory=generate_uuid)
    goal_id: str = Field(..., description="Associated parent Goal ID")
    assigned_agent_id: Optional[str] = Field(default=None)
    name: str = Field(..., description="Task title")
    description: str = Field(..., description="Detailed task requirements")
    required_capability: str = Field(..., description="Capability required to execute this task")
    priority: str = Field(default="medium", description="Task priority: high / medium / low")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExecutionPlan(BaseModel):
    """
    Ordered sequence of Tasks constructed by the Supervisor Planner to fulfill a Goal.

    Attributes:
        id: Unique plan identifier.
        goal_id: Parent Goal reference.
        tasks: Sequenced list of Tasks to be executed.
    """

    id: str = Field(default_factory=generate_uuid)
    goal_id: str = Field(..., description="Target Goal ID")
    tasks: List[Task] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskResult(BaseModel):
    """
    Structured outcome returned by an Agent after processing a Task.

    Attributes:
        task_id: Associated Task ID.
        agent_id: Identifier of the executing agent.
        status: Task execution outcome.
        summary: Output content produced by the agent.
        metadata: Execution metrics and telemetry.
        error: Error details if execution failed.
    """

    task_id: str = Field(..., description="Associated Task ID")
    agent_id: str = Field(..., description="Agent that executed the task")
    status: TaskStatus = Field(..., description="Execution outcome status")
    summary: str = Field(..., description="Human-readable summary of the result")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = Field(default=None, description="Error message if failed")
    completed_at: datetime = Field(default_factory=datetime.utcnow)


class ValidationResult(BaseModel):
    """
    Outcome of SupervisorValidator evaluation on a TaskResult.

    Attributes:
        task_id: Evaluated Task ID.
        is_valid: Boolean status of validation check.
        reason: Explanatory validation notes.
    """

    task_id: str
    is_valid: bool
    reason: str
    validated_at: datetime = Field(default_factory=datetime.utcnow)


class ExecutionResult(BaseModel):
    """
    Final aggregated response produced by SupervisorReportGenerator and returned to caller.

    Attributes:
        goal_id: Parent Goal ID.
        status: Overall orchestration status (success, partial, failed).
        response: Final synthesized text payload.
        tasks: List of individual TaskResult records.
    """

    goal_id: str
    status: str = Field(..., description="overall: success | partial | failed")
    response: str = Field(..., description="Synthesized final response text")
    tasks: List[TaskResult] = Field(default_factory=list)
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
        call_id: Unique ID for correlating calls with results.
        tool_name: Registry name of the tool to invoke.
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
        call_id: Correlates to the originating ToolCall.
        tool_name: Name of the tool that produced this result.
        output: String representation of the tool's output.
        error: Non-None when execution raised an exception.
        success: False when tool raised an error.
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
        step: Index of the reasoning loop iteration (1-based).
        tool_result: Underlying ToolResult from the registry.
        content: Human-readable summary injected into the next prompt.
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
        step: 1-based iteration index.
        thought: LLM's internal reasoning text.
        action: Name of the chosen tool (None if final answer step).
        action_input: Parameters passed to the tool.
        observation: Tool result summary (None on final answer steps).
        is_final: True when the LLM produced a Final Answer instead of an action.
        final_answer: Populated only when is_final=True.
    """

    step: int = Field(..., description="Iteration index (1-based)")
    thought: str = Field(..., description="LLM reasoning text for this step")
    action: Optional[str] = Field(default=None, description="Tool name selected, if any")
    action_input: Optional[Dict[str, Any]] = Field(default=None)
    observation: Optional[str] = Field(default=None, description="Observation from tool result")
    is_final: bool = Field(default=False, description="True when this step produces the answer")
    final_answer: Optional[str] = Field(default=None, description="Answer text when is_final=True")
