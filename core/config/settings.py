"""
Application Settings & Configuration Loader

Centralizes environment variables and runtime settings using Pydantic Settings.
Reads configuration from environment variables or .env file with zero hardcoded credentials.

Architecture Layer: Core / Config
"""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """
    LLM Provider Credentials & Global Settings.

    Stores API keys and default provider selection. API keys are loaded directly
    from environment variables (e.g. GEMINI_API_KEY) and never checked into code.
    """

    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")

    default_provider: str = Field(default="gemini", alias="DEFAULT_LLM_PROVIDER")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class DatabaseSettings(BaseSettings):
    """
    Database Connection Parameters.

    Encapsulates connection configuration for PostgreSQL / vector stores.
    """

    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="agentos_db", alias="DB_NAME")
    db_user: str = Field(default="agentos", alias="DB_USER")
    db_password: str = Field(default="agentos_secret", alias="DB_PASSWORD")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class Settings(BaseSettings):
    """
    Master Application Configuration Settings.

    Aggregates application, server, database, and LLM configuration settings.
    Exposed as a global `settings` instance for convenience, though dependency injection
    is preferred when passing settings to factories.
    """

    app_name: str = Field(default="AgentOS", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    llm: LLMSettings = Field(default_factory=LLMSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


# Global Settings Instance for quick reference across modules
settings = Settings()
