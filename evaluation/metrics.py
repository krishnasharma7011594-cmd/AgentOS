"""Evaluation metrics interface."""

from abc import ABC, abstractmethod
from typing import Dict


class BaseEvaluationMetric(ABC):
    """Abstract interface for evaluating agent output quality."""

    @abstractmethod
    def evaluate(self, prediction: str, reference: str) -> Dict[str, float]:
        """Compute metric score for prediction against reference."""
        pass
