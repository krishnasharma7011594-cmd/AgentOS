"""
Base LLM Provider Interface

Defines the abstract interface for all LLM providers in AgentOS.
Ensures vendor-neutral interaction: Agents and Supervisor invoke BaseLLMProvider methods
without knowing whether Gemini, Groq, OpenAI, or a local model is backing the execution.

Architecture Layer: Core / AI / Providers
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, List, Optional

from core.models.domain import Message


class BaseLLMProvider(ABC):
    """
    Abstract Base Class for LLM API wrappers.

    Decouples core agent reasoning from concrete provider APIs (Gemini, Groq, OpenAI).
    Concrete subclasses handle SDK initialization, format conversions, retries, and errors.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initializes the provider with an optional API key override."""
        self.api_key = api_key

    @abstractmethod
    async def generate_response(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Message:
        """Generates a non-streaming completion given a list of input messages."""
        pass

    @abstractmethod
    def generate_stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Generates a streaming completion iterator."""
        pass

    async def complete(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """
        Convenience wrapper around generate_response returning text string content directly.
        """
        res = await self.generate_response(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return res.content
