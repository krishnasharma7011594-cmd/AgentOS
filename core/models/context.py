"""
Context Domain Models

Defines the core data structures for the Intelligent Context Engine (Phase 8).
All models are strictly serializable. ContextBundle and ContextItem are
immutable (frozen) by design to guarantee state safety when passed to
agents and planners.

Architecture Layer: Core / Models
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ContextScope(str, Enum):
    """The intended consumer of the context."""
    PLANNER = "planner"
    SUPERVISOR = "supervisor"
    AGENT = "agent"


class ContextPriority(str, Enum):
    """Importance level of a retrieved context item."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ContextSource(str, Enum):
    """The origin subsystem/layer of the context item."""
    MEMORY = "memory"
    REFLECTION = "reflection"
    EXECUTION = "execution"
    KNOWLEDGE = "knowledge"
    DOCUMENT = "document"


class ContextReason(BaseModel):
    """Explains why a specific item was included in the context bundle."""
    strategy_name: str = Field(..., description="The strategy that retrieved this item.")
    explanation: str = Field(..., description="Human-readable explanation for inclusion.")


class ContextMetrics(BaseModel):
    """Operational metrics tracked during context generation."""
    generation_latency_ms: float = 0.0
    items_retrieved: int = 0
    items_discarded: int = 0
    strategy_latencies_ms: Dict[str, float] = Field(default_factory=dict)
    strategy_yields: Dict[str, int] = Field(default_factory=dict)


class ContextItem(BaseModel):
    """
    A single piece of relevant knowledge.
    Immutable to guarantee state safety during execution.
    """
    model_config = ConfigDict(frozen=True)

    content: str = Field(..., description="The actual knowledge payload.")
    source: ContextSource = Field(..., description="Origin of the knowledge.")
    priority: ContextPriority = Field(..., description="Importance level.")
    reason: ContextReason = Field(..., description="Why this item is relevant.")
    relevance_score: float = Field(0.0, description="Normalized score [0.0, 1.0].")
    
    # Provenance fields for explainability and debugging
    memory_id: Optional[str] = Field(None, description="Original MemoryRecord ID.")
    collection: Optional[str] = Field(None, description="Source collection.")
    retrieval_strategy: str = Field(..., description="Name of the strategy that fetched this.")
    retrieval_timestamp: float = Field(..., description="When it was retrieved (epoch).")


class ContextBundle(BaseModel):
    """
    An assembled, ranked, and normalized set of ContextItems.
    Immutable. Passed to Planners, Supervisors, and Agents.
    """
    model_config = ConfigDict(frozen=True)

    items: List[ContextItem] = Field(default_factory=list, description="Ranked items.")
    scope: ContextScope = Field(..., description="Intended consumer.")
    metrics: ContextMetrics = Field(default_factory=ContextMetrics, description="Generation stats.")

    @property
    def is_empty(self) -> bool:
        return len(self.items) == 0


class ContextSelectionPolicy(BaseModel):
    """Rules dictating *what* can be retrieved."""
    allowed_sources: Optional[List[ContextSource]] = None
    allowed_collections: Optional[List[str]] = None
    exclude_tags: List[str] = Field(default_factory=list)


class ContextAssemblyPolicy(BaseModel):
    """Rules dictating *how* a bundle is constructed."""
    max_items: int = Field(10, description="Maximum items in the final bundle.")
    min_relevance_score: float = Field(0.0, description="Minimum score required.")
    enforce_deduplication: bool = Field(True, description="Whether to deduplicate by memory_id.")


class ContextRequest(BaseModel):
    """
    Request object sent to the ContextEngine.
    Captures the current execution state and context requirements.
    """
    goal_id: str
    goal_description: str
    scope: ContextScope
    
    # Optional state constraints
    task_id: Optional[str] = None
    task_description: Optional[str] = None
    current_status: Optional[str] = None
    
    # Overrides (if none provided, default DI policies apply)
    selection_policy: Optional[ContextSelectionPolicy] = None
    assembly_policy: Optional[ContextAssemblyPolicy] = None


class PlannerInput(BaseModel):
    """
    Input object passed to the Planner.
    Wraps the raw string instructions and the structured ContextBundle.
    """
    goal_id: str
    goal_description: str
    context: Optional[ContextBundle] = None
