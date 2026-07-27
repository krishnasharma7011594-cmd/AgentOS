"""
ExecutionContext (execution module home)

Re-exports ExecutionContext from core.models.domain for cleaner imports
from the execution subsystem. The model itself stays in domain.py to
avoid circular imports, but callers can import from here as the subsystem grows.

Architecture Layer: Core / Execution
"""

from core.models.domain import ExecutionContext  # noqa: F401

__all__ = ["ExecutionContext"]
