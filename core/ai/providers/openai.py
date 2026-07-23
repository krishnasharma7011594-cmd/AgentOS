"""
OpenAI LLM Provider Skeleton Implementation.

Architecture Layer: Core / AI / Providers
"""

from typing import Any, AsyncIterator, List, Optional

from core.ai.providers.base import BaseLLMProvider
from core.config.settings import settings
from core.models.domain import Message, RoleEnum
from core.utils.helpers import generate_uuid


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider skeleton (placeholder, not wired)."""

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or settings.llm.openai_api_key
        super().__init__(api_key=key)

    async def generate_response(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Message:
        """Placeholder skeleton for OpenAI generation."""
        return Message(
            id=generate_uuid(),
            role=RoleEnum.ASSISTANT,
            content="[OpenAI Provider Skeleton Response]",
            metadata={"provider": "openai", "model": "gpt-4o"},
        )

    def generate_stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Placeholder streaming skeleton for OpenAI."""

        async def _stream() -> AsyncIterator[str]:
            yield "OpenAI stream placeholder"

        return _stream()
