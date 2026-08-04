from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class CapabilityScope(str, Enum):
    """Defines the operating scope of a capability."""
    GLOBAL = "GLOBAL"
    LOCAL = "LOCAL"
    SESSION = "SESSION"


class CapabilityVersion(BaseModel):
    """Semantic versioning model for capabilities."""
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def is_compatible_with(self, other: "CapabilityVersion") -> bool:
        """Simple compatibility check (same major version, other is <= this version)."""
        if self.major != other.major:
            return False
        if self.minor < other.minor:
            return False
        if self.minor == other.minor and self.patch < other.patch:
            return False
        return True


class CapabilityMetadata(BaseModel):
    """Metadata describing a capability."""
    name: str = Field(..., description="Unique name of the capability")
    version: CapabilityVersion = Field(..., description="Version of the capability")
    description: str = Field(..., description="Human readable explanation")
    author: str = Field(default="AgentOS", description="Author or provider of the capability")


class CapabilityPermission(BaseModel):
    """Describes a required permission to execute a capability."""
    resource: str = Field(..., description="The resource being accessed (e.g., filesystem, network)")
    action: str = Field(..., description="The action being performed (e.g., read, write)")

    def __str__(self) -> str:
        return f"{self.resource}.{self.action}"


class CapabilityDependency(BaseModel):
    """Describes a dependency on another capability."""
    capability_name: str
    minimum_version: Optional[CapabilityVersion] = None


class CapabilityPolicy(BaseModel):
    """Constraints on the capability."""
    rate_limit_per_minute: Optional[int] = None
    timeout_ms: Optional[int] = None
    max_concurrent_executions: Optional[int] = None


class CapabilityDescriptor(BaseModel):
    """Full definition of an available capability."""
    metadata: CapabilityMetadata
    scope: CapabilityScope = CapabilityScope.LOCAL
    permissions: List[CapabilityPermission] = Field(default_factory=list)
    dependencies: List[CapabilityDependency] = Field(default_factory=list)
    policy: CapabilityPolicy = Field(default_factory=CapabilityPolicy)


class CapabilityRequest(BaseModel):
    """Request from an agent to execute a capability."""
    capability_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    preferred_version: Optional[CapabilityVersion] = None
    minimum_version: Optional[CapabilityVersion] = None
    context_data: Optional[Dict[str, Any]] = None


class ResolvedCapability(BaseModel):
    """Output from CapabilityEngine indicating the resolved tool implementation."""
    request: CapabilityRequest
    descriptor: CapabilityDescriptor
    tool_name: str
    tool_version: CapabilityVersion


class CapabilityResult(BaseModel):
    """Standardized result wrapper for capability execution."""
    success: bool
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
