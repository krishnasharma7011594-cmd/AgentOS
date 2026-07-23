"""Base input/output validator interface."""

from abc import ABC, abstractmethod
from typing import Any, Tuple


class BaseValidator(ABC):
    """Abstract interface for validating inputs or agent execution artifacts."""

    @abstractmethod
    def validate(self, artifact: Any) -> Tuple[bool, str]:
        """Validate artifact and return (is_valid, reason)."""
        pass
