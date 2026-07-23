"""
Groq LLM Provider

Concrete implementation of BaseLLMProvider backed by the Groq async SDK.
Provides high-throughput inference using Llama 3 models on Groq LPUs.

Architecture Layer: Core / AI / Providers
"""

from typing import Any, AsyncIterator, List, Optional

from core.ai.providers.base import BaseLLMProvider
from core.config.settings import settings
from core.exceptions.base import LLMProviderError, MissingAPIKeyError
from core.logging.logger import logger
from core.models.domain import Message, RoleEnum
from core.utils.helpers import generate_uuid


class GroqProvider(BaseLLMProvider):
    """
    LLM Provider for Groq LPU inference engines (default model: llama-3.3-70b-versatile).

    Lazy-loads `AsyncGroq` client to ensure startup proceeds smoothly even if credentials
    or SDK dependencies are absent.
    """

    MODEL_NAME = "llama-3.3-70b-versatile"

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or settings.llm.groq_api_key
        if not key:
            raise MissingAPIKeyError(
                "GROQ_API_KEY is not set.",
                details="Add GROQ_API_KEY to your .env file.",
            )
        super().__init__(api_key=key)
        self._client: Any = None

    def _get_client(self) -> Any:
        """
        Lazy-loads the AsyncGroq SDK client.

        Raises:
            LLMProviderError: If the groq package is missing.
        """
        if self._client is None:
            try:
                from groq import AsyncGroq

                self._client = AsyncGroq(api_key=self.api_key)
            except ImportError as exc:
                raise LLMProviderError(
                    "groq package is not installed.",
                    details="Run: pip install groq",
                ) from exc
        return self._client

    @staticmethod
    def _to_groq_messages(messages: List[Message]) -> List[dict[str, str]]:
        """Converts AgentOS Message instances into OpenAI/Groq chat dictionary format."""
        role_map = {
            "user": "user",
            "assistant": "assistant",
            "system": "system",
            "agent": "assistant",
            "tool": "user",
        }
        return [
            {"role": role_map.get(m.role.value, "user"), "content": m.content} for m in messages
        ]

    async def generate_response(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Message:
        """Asynchronously dispatches a chat completion request to the Groq API."""
        logger.info("GroqProvider: generating response", model=self.MODEL_NAME)
        try:
            client = self._get_client()
            groq_messages = self._to_groq_messages(messages)

            completion = await client.chat.completions.create(
                model=self.MODEL_NAME,
                messages=groq_messages,
                temperature=temperature,
                **({"max_tokens": max_tokens} if max_tokens else {}),
            )
            content = completion.choices[0].message.content or ""
            logger.info("GroqProvider: response received", chars=len(content))
            return Message(
                id=generate_uuid(),
                role=RoleEnum.ASSISTANT,
                content=content,
                metadata={
                    "provider": "groq",
                    "model": self.MODEL_NAME,
                    "usage": dict(completion.usage) if completion.usage else {},
                },
            )
        except MissingAPIKeyError:
            raise
        except LLMProviderError:
            raise
        except Exception as exc:
            logger.error("GroqProvider: API call failed", error=str(exc))
            raise LLMProviderError(
                f"Groq API call failed: {exc}",
                details=str(exc),
            ) from exc

    def generate_stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Streaming response generator placeholder."""

        async def _stream() -> AsyncIterator[str]:
            response = await self.generate_response(messages, temperature=temperature, **kwargs)
            yield response.content

        return _stream()
