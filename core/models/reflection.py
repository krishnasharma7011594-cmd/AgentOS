"""
Reflection Domain Models

Defines the domain entities for Phase 6: Reflective Supervisor.
Reflection transforms AgentOS from an adaptive system into a learning system.

These models are strictly for read-only analysis of completed executions.
They do not influence active workflow execution.

Architecture Layer: Core / Models
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List

from pydantic import BaseModel, Field

from core.utils.helpers import generate_uuid


class ReflectionCategory(str, Enum):
    """Categorization for reflection observations and recommendations."""

    PLANNING = "planning"
    EXECUTION = "execution"
    RETRY = "retry"
    REPLAN = "replan"
    CAPABILITY_SELECTION = "capability_selection"
    TASK_DEPENDENCY = "task_dependency"
    PERFORMANCE = "performance"
    FAILURE_RECOVERY = "failure_recovery"
    RESOURCE_USAGE = "resource_usage"


class ReflectionSeverity(str, Enum):
    """Severity level of a reflection observation."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReflectionObservation(BaseModel):
    """
    A single factual finding observed from the completed execution.

    Attributes:
        id:          Stable unique identifier for the observation.
        category:    The general domain this observation falls under.
        severity:    Impact or importance level.
        description: Human-readable statement of what was observed.
        evidence:    Data supporting the observation (e.g. task IDs, metrics).
    """

    id: str = Field(default_factory=generate_uuid, description="Stable unique identifier")
    category: ReflectionCategory = Field(..., description="Domain of the observation")
    severity: ReflectionSeverity = Field(..., description="Impact level")
    description: str = Field(..., description="What was observed")
    evidence: str = Field(..., description="Data supporting the observation")


class ReflectionRecommendation(BaseModel):
    """
    Advisory suggestion generated from a specific observation.

    Recommendations never automatically change system behavior; they exist
    for future planning phases or human review.

    Attributes:
        observation_id:        ID of the ReflectionObservation that triggered this.
        category:              Domain of the recommendation (usually matches observation).
        evidence:              Context explaining why this is recommended.
        explanation:           Why the current behavior was suboptimal.
        suggested_improvement: Actionable advice for future executions.
    """

    observation_id: str = Field(..., description="Link to originating observation")
    category: ReflectionCategory = Field(..., description="Domain of recommendation")
    evidence: str = Field(..., description="Context explaining why this is recommended")
    explanation: str = Field(..., description="Why current behavior was suboptimal")
    suggested_improvement: str = Field(..., description="Actionable advice")


class ReflectionScore(BaseModel):
    """
    Deterministic scoring (0-100) across multiple execution dimensions.

    Scores are intended for comparison across executions, not absolute truth.
    """

    planning_quality: int = Field(default=100, ge=0, le=100)
    execution_efficiency: int = Field(default=100, ge=0, le=100)
    failure_recovery: int = Field(default=100, ge=0, le=100)
    agent_selection: int = Field(default=100, ge=0, le=100)
    task_efficiency: int = Field(default=100, ge=0, le=100)
    overall_score: int = Field(default=100, ge=0, le=100)


class ReflectionMetrics(BaseModel):
    """
    Observability metrics specific to the Reflection subsystem itself.
    """

    reflection_duration_ms: float = Field(default=0.0)
    observation_count: int = Field(default=0)
    recommendation_count: int = Field(default=0)
    average_score: float = Field(default=0.0)


class ExecutionReview(BaseModel):
    """
    Structured container populated during the review phase before scoring/recommending.
    """

    goal_id: str = Field(..., description="Goal that was executed")
    observations: List[ReflectionObservation] = Field(default_factory=list)


class ReflectionReport(BaseModel):
    """
    Complete output of the ReflectionEngine.

    Attached to the final ExecutionResult to provide explainable feedback
    for the completed workflow.

    Attributes:
        reflection_version:   Version of the reflection schema/engine.
        execution_summary:    Brief text summary of what happened.
        observations:         All factual findings.
        recommendations:      All suggested improvements.
        scores:               Deterministic execution scores.
        metrics:              Telemetry about the reflection process itself.
        decision_summary:     Breakdown of supervisor decisions made.
        retry_analysis:       Summary of retry behavior and effectiveness.
        replanning_analysis:  Summary of replan behavior and effectiveness.
        generated_at:         Timestamp of report generation.
    """

    reflection_version: str = Field(default="1.0", description="Schema version")
    execution_summary: str = Field(..., description="Brief summary of execution")
    observations: List[ReflectionObservation] = Field(default_factory=list)
    recommendations: List[ReflectionRecommendation] = Field(default_factory=list)
    scores: ReflectionScore = Field(default_factory=ReflectionScore)
    metrics: ReflectionMetrics = Field(default_factory=ReflectionMetrics)

    # Detailed sub-analyses
    decision_summary: str = Field(default="")
    retry_analysis: str = Field(default="")
    replanning_analysis: str = Field(default="")

    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
