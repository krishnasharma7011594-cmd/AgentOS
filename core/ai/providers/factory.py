"""
LLM Provider Factory

Constructs and returns the configured BaseLLMProvider implementation based on application settings.
Ensures dependency inversion: agents depend strictly on the BaseLLMProvider abstraction.

Architecture Layer: Core / AI / Providers
"""

from typing import Optional

from core.ai.providers.base import BaseLLMProvider
from core.config.settings import Settings
from core.exceptions.base import LLMProviderError
from core.logging.logger import logger


def build_llm_provider(settings: Settings, api_key: Optional[str] = None) -> BaseLLMProvider:
    """
    Factory function instantiating a concrete BaseLLMProvider based on settings.

    Decouples AgentOS modules from specific provider classes. Switching from Gemini
    to Groq (or OpenAI in future) requires only updating configuration without changing agent code.

    Args:
        settings: Application Settings object containing LLM provider configuration.
        api_key: Optional explicit API key override.

    Returns:
        BaseLLMProvider: Initialized provider instance (GeminiProvider or GroqProvider).

    Raises:
        LLMProviderError: If the configured provider key is unmapped.
    """
    provider_name = settings.llm.default_provider.lower()
    logger.info("LLM factory: building provider", provider=provider_name)

    if provider_name == "gemini":
        from core.ai.providers.gemini import GeminiProvider

        return GeminiProvider(api_key=api_key or settings.llm.gemini_api_key)

    if provider_name == "groq":
        from core.ai.providers.groq import GroqProvider

        return GroqProvider(api_key=api_key or settings.llm.groq_api_key)

    # TODO: Add support for OpenAI and local Ollama/vLLM provider implementations.
    raise LLMProviderError(
        f"Unknown LLM provider: '{provider_name}'.",
        details="Set DEFAULT_LLM_PROVIDER to 'gemini' or 'groq' in .env",
    )
