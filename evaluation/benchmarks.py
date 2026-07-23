"""Benchmark suite runner interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseBenchmarkRunner(ABC):
    """Abstract interface for running agent benchmarks."""

    @abstractmethod
    async def run_benchmark(self, suite_name: str) -> Dict[str, Any]:
        """Execute benchmark suite and return score report."""
        pass
