"""Tests for LLM Providers (using Mock Provider)."""

from typing import Any, AsyncIterator, List, Optional

import pytest

from core.ai.providers.base import BaseLLMProvider
from core.models.domain import Message, RoleEnum
from core.utils.helpers import generate_uuid


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, response_text: str = "Mock response output"):
        super().__init__(api_key="mock_key")
        self.response_text = response_text

    async def generate_response(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Message:
        return Message(
            id=generate_uuid(),
            role=RoleEnum.ASSISTANT,
            content=self.response_text,
            metadata={"provider": "mock", "model": "mock-model"},
        )

    async def generate_stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        yield self.response_text


@pytest.mark.asyncio
async def test_mock_llm_provider_generate_response() -> None:
    provider = MockLLMProvider("LangGraph is a library for building stateful agent workflows.")
    messages = [Message(id="1", role=RoleEnum.USER, content="Explain LangGraph")]
    response = await provider.generate_response(messages)

    assert response.role == RoleEnum.ASSISTANT
    assert "LangGraph" in response.content
    assert response.metadata["provider"] == "mock"
