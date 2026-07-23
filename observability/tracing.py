"""Distributed tracing interface for AgentOS."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTracer(ABC):
    """Abstract interface for tracing agent executions and task spans."""

    @abstractmethod
    def start_span(self, name: str, attributes: Dict[str, Any] | None = None) -> Any:
        """Start a trace span."""
        pass
