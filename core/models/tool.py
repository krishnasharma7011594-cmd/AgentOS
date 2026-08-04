import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from core.models.capability import (
    CapabilityPermission,
    CapabilityRequest,
    CapabilityVersion,
    ResolvedCapability,
)


class ToolCategory(str, Enum):
    """Broad categories for tools to aid in discovery and organization."""

    SYSTEM = "SYSTEM"
    BROWSER = "BROWSER"
    FILESYSTEM = "FILESYSTEM"
    NETWORK = "NETWORK"
    DATABASE = "DATABASE"
    DEVELOPMENT = "DEVELOPMENT"
    COMMUNICATION = "COMMUNICATION"
    KNOWLEDGE = "KNOWLEDGE"
    FINANCE = "FINANCE"
    CLOUD = "CLOUD"
    AUTOMATION = "AUTOMATION"
    MOCK = "MOCK"


class ToolHealth(BaseModel):
    """Health metadata for a tool."""

    status: str = Field(default="UNKNOWN", description="e.g., HEALTHY, DEGRADED, UNHEALTHY")
    availability: float = Field(
        default=1.0, description="0.0 to 1.0 indicating uptime/availability"
    )
    latency_ms: Optional[int] = None
    last_error: Optional[str] = None
    last_checked: Optional[datetime.datetime] = None
    version: Optional[CapabilityVersion] = None


class ToolManifest(BaseModel):
    """Discoverable metadata for a tool plugin."""

    name: str
    version: CapabilityVersion
    description: str
    author: str = "AgentOS"
    capabilities: List[str] = Field(default_factory=list)
    permissions: List[CapabilityPermission] = Field(default_factory=list)
    required_resources: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    category: ToolCategory = ToolCategory.SYSTEM
    entry_point: str = Field(..., description="Module path to the tool class")


class ResourceLease(BaseModel):
    """A lease object representing a granted resource."""

    lease_id: str
    resource_name: str
    granted_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    expires_at: Optional[datetime.datetime] = None
    owner_id: str


class ToolExecutionContext(BaseModel):
    """Structured context passed to a tool during execution."""

    execution_id: str
    request: CapabilityRequest
    capability: ResolvedCapability
    permissions: List[CapabilityPermission] = Field(default_factory=list)
    resource_leases: List[ResourceLease] = Field(default_factory=list)
    # Using Any for cancellation token to avoid circular deps if defined elsewhere,
    # but could be typed properly if imported.
    cancellation_token: Any = None
    agent_id: Optional[str] = None
    supervisor_id: Optional[str] = None
    execution_metadata: Dict[str, Any] = Field(default_factory=dict)
