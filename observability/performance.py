"""Performance profiling interface."""

from abc import ABC, abstractmethod


class BasePerformanceProfiler(ABC):
    """Abstract interface for profiling latency and resource consumption."""

    @abstractmethod
    def log_latency(self, component: str, duration_ms: float) -> None:
        """Log latency for a component operation."""
        pass
