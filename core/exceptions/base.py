"""
Domain Exception Hierarchy

Defines custom, domain-specific exception types for AgentOS.
Provides granular error handling across supervisor, router, registry, and provider layers.

Architecture Layer: Core / Exceptions
"""


class AgentOSError(Exception):
    """
    Base exception class for all AgentOS errors.

    Captures human-readable error messages alongside structured metadata context.
    """

    def __init__(self, message: str, details: str | None = None):
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | details: {self.details}"
        return self.message


class AgentNotFoundError(AgentOSError):
    """Raised when a requested agent is missing from the AgentRegistry."""

    pass


class CapabilityNotFoundError(AgentOSError):
    """Raised when no registered agent satisfies a required capability in CapabilityRegistry."""

    pass


class ToolExecutionError(AgentOSError):
    """Raised when tool execution fails or violates security policy rules."""

    pass


class LLMProviderError(AgentOSError):
    """Raised when an external LLM provider API call fails or encounters an unrecoverable error."""

    pass


class MissingAPIKeyError(AgentOSError):
    """Raised when required LLM provider credentials are missing from settings."""

    pass


class TaskQueueError(AgentOSError):
    """Raised when task queue submission or worker execution fails."""

    pass


class SecurityPolicyError(AgentOSError):
    """Raised when action validation violates security or sandbox policy."""

    pass


class PlanningError(AgentOSError):
    """Raised when the Supervisor Planner cannot generate an execution plan."""

    pass


class ValidationError(AgentOSError):
    """Raised when a TaskResult fails structural or semantic validation."""

    pass
