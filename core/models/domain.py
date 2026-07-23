"""
Core Domain Models

Defines the foundational domain entities and data schemas for AgentOS using Pydantic.
Ensures strong typing, serialization, and schema validation across all application layers.

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
