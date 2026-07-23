"""Prompt repository base interface."""

from abc import ABC, abstractmethod


class BasePromptRepository(ABC):
    """Abstract interface for loading prompt definitions."""

    @abstractmethod
    def get_prompt(self, name: str) -> str:
        """Fetch raw prompt string by key name."""
        pass
