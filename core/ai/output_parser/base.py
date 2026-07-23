"""Base output parser interface for AgentOS."""

from abc import ABC, abstractmethod
from typing import Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseOutputParser(ABC):
    """Abstract interface for parsing raw LLM responses into structured Pydantic models."""

    @abstractmethod
    def parse(self, text: str, schema: Type[T]) -> T:
        """Parse raw LLM text output into structured target schema."""
        pass
