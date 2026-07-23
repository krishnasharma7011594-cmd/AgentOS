"""
Google Gemini LLM Provider

Concrete implementation of BaseLLMProvider backed by the google-generativeai SDK.
Handles prompt formatting, API invocation, and error handling for Gemini models.

Architecture Layer: Core / AI / Providers
"""

from typing import Any, AsyncIterator, List, Optional

from core.ai.providers.base import BaseLLMProvider
from core.config.settings import settings
from core.exceptions.base import LLMProviderError, MissingAPIKeyError
from core.logging.logger import logger
from core.models.domain import Message, RoleEnum
from core.utils.helpers import generate_uuid


class GeminiProvider(BaseLLMProvider):
    """
    LLM Provider for Google Gemini models (default model: gemini-1.5-flash).

    Lazy-loads the `google.generativeai` SDK on first request to prevent startup failures
    if the SDK dependency or API key is unconfigured.
    """

    MODEL_NAME = "gemini-1.5-flash"

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or settings.llm.gemini_api_key
        if not key:
            raise MissingAPIKeyError(
                "GEMINI_API_KEY is not set.",
                details="Add GEMINI_API_KEY to your .env file.",
            )
        super().__init__(api_key=key)
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-loads and configures the Gemini SDK client."""
        if self._client is None:
            try:
                import google.generativeai as genai

                genai.configure(api_key=self.api_key)  # type: ignore[attr-defined]
                self._client = genai.GenerativeModel(self.MODEL_NAME)  # type: ignore[attr-defined]
            except (ImportError, AttributeError) as exc:
                raise LLMProviderError(
                    "google-generativeai package is not installed or configured.",
                    details="Run: pip install google-generativeai",
                ) from exc
        return self._client

    def _build_prompt(self, messages: List[Message]) -> str:
        """Flattens structured Message list into a Gemini prompt sequence."""
        parts: List[str] = []
        for msg in messages:
            prefix = msg.role.value.upper()
            parts.append(f"{prefix}: {msg.content}")
        return "\n".join(parts)

    async def generate_response(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Message:
        """Executes a completion request against Gemini API."""
        logger.info("GeminiProvider: generating response", model=self.MODEL_NAME)
        try:
            client = self._get_client()
            prompt = self._build_prompt(messages)

            import asyncio

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.generate_content(
                    prompt,
                    generation_config={
                        "temperature": temperature,
                        **({"max_output_tokens": max_tokens} if max_tokens else {}),
                    },
                ),
            )
            content = str(response.text)
            logger.info("GeminiProvider: response received", chars=len(content))
            return Message(
                id=generate_uuid(),
                role=RoleEnum.ASSISTANT,
                content=content,
                metadata={"provider": "gemini", "model": self.MODEL_NAME},
            )
        except MissingAPIKeyError:
            raise
        except LLMProviderError:
            raise
        except Exception as exc:
            logger.error("GeminiProvider: API call failed", error=str(exc))
            raise LLMProviderError(
                f"Gemini API call failed: {exc}",
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
