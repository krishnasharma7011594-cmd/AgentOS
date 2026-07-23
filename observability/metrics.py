"""System metrics interface."""

from abc import ABC, abstractmethod


class BaseMetricsCollector(ABC):
    """Abstract interface for collecting system metrics."""

    @abstractmethod
    def increment_counter(self, metric_name: str, value: int = 1) -> None:
        """Increment a metric counter."""
        pass

    @abstractmethod
    def record_gauge(self, metric_name: str, value: float) -> None:
        """Record gauge value."""
        pass
