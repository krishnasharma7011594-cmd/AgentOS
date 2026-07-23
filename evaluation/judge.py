"""LLM-as-a-Judge interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseLLMJudge(ABC):
    """Abstract interface for LLM-as-a-judge automated evaluations."""

    @abstractmethod
    async def judge_output(self, prompt: str, response: str) -> Dict[str, Any]:
        """Score output quality using LLM judge."""
        pass
