"""
Configuration management using pydantic-settings.

This module centralizes all configuration for the research engine,
including LLM endpoints, pipeline parameters, and logging settings.
All settings can be overridden via environment variables or .env file.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with validation and defaults.

    Settings are loaded in the following order of precedence:
    1. Environment variables (e.g., OPENAI_API_KEY)
    2. .env file in project root
    3. Default values defined here

    Example usage:
        settings = Settings()
        print(settings.openai_api_base)
    """

    # =========================================================================
    # LLM Configuration
    # =========================================================================

    openai_api_key: str = Field(
        default="lm-studio",
        description="API key for LLM provider (use 'lm-studio' for local LM Studio)",
    )

    openai_api_base: str = Field(
        default="http://localhost:1234/v1",
        description="Base URL for OpenAI-compatible API endpoint",
    )

    openai_model_name: str = Field(
        default="qwen/qwen3.5-4b",
        description="Model name to use for LLM calls",
    )

    openai_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Temperature for LLM generation (0.0=deterministic, 1.0=creative)",
    )

    openai_max_tokens: int = Field(
        default=12288,
        gt=0,
        description="Maximum tokens in LLM response",
    )

    openai_timeout: int = Field(
        default=120,
        gt=0,
        description="Request timeout in seconds",
    )

    langchain_tracing_v2: bool = Field(
        default=False,
        description="Enable LangSmith tracing via LANGCHAIN_TRACING_V2",
    )

    langchain_api_key: str = Field(default="", description="LangSmith API key")

    langchain_project: str = Field(
        default="search-summarization-engine",
        description="LangSmith project name",
    )

    langchain_endpoint: str = Field(
        default="https://api.smith.langchain.com",
        description="LangSmith API endpoint",
    )

    # =========================================================================
    # Pipeline Configuration
    # =========================================================================

    num_search_queries: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Number of search queries to generate per user question",
    )

    num_search_results_per_query: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of search result URLs to fetch per query",
    )

    result_text_max_characters: int = Field(
        default=10000,
        gt=0,
        description="Maximum characters to extract from each scraped web page",
    )

    search_delay_seconds: float = Field(
        default=1.0,
        ge=0.0,
        description="Delay between search requests to avoid rate limiting",
    )

    scraper_timeout_seconds: int = Field(
        default=15,
        gt=0,
        description="Timeout for web scraping HTTP requests",
    )

    # =========================================================================
    # Logging Configuration
    # =========================================================================

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    log_format: Literal["json", "text"] = Field(
        default="json",
        description="Log output format",
    )

    log_file: str = Field(
        default="logs/research_engine.log",
        description="Path to log file (relative to project root)",
    )

    log_console: bool = Field(
        default=True,
        description="Enable console logging",
    )

    # =========================================================================
    # Advanced Settings
    # =========================================================================

    enable_parallel_processing: bool = Field(
        default=True,
        description="Enable parallel processing for independent operations",
    )

    max_concurrent_scrapes: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum concurrent web scraping tasks",
    )

    llm_retry_attempts: int = Field(
        default=3,
        ge=0,
        description="Number of retry attempts for failed LLM calls",
    )

    llm_retry_backoff: float = Field(
        default=2.0,
        gt=0.0,
        description="Exponential backoff multiplier for retries (seconds)",
    )

    # =========================================================================
    # Output Configuration
    # =========================================================================

    output_dir: str = Field(
        default="reports",
        description="Default output directory for generated reports",
    )

    output_format: Literal["markdown", "html", "text"] = Field(
        default="markdown",
        description="Default report output format",
    )

    include_citations: bool = Field(
        default=True,
        description="Include citations/URLs in generated reports",
    )

    include_search_queries: bool = Field(
        default=True,
        description="Include generated search queries in reports",
    )

    # =========================================================================
    # Pydantic Settings Configuration
    # =========================================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields in .env
    )

    # =========================================================================
    # Validators
    # =========================================================================

    @field_validator("openai_api_base")
    @classmethod
    def validate_api_base(cls, v: str) -> str:
        """Ensure API base URL has correct format."""
        v = v.rstrip("/")
        if not v.endswith("/v1"):
            v = f"{v}/v1"
        return v

    @field_validator("log_file")
    @classmethod
    def validate_log_file(cls, v: str) -> str:
        """Ensure log file path is absolute or relative to project root."""
        log_path = Path(v)
        if not log_path.is_absolute():
            # Make relative to project root
            project_root = Path(__file__).parent.parent.parent
            log_path = project_root / v
        return str(log_path)

    # =========================================================================
    # Computed Properties
    # =========================================================================

    @property
    def project_root(self) -> Path:
        """Get project root directory."""
        return Path(__file__).parent.parent.parent

    @property
    def prompts_dir(self) -> Path:
        """Get prompts directory path."""
        return self.project_root / "src" / "prompts"

    @property
    def logs_dir(self) -> Path:
        """Get logs directory path."""
        return Path(self.log_file).parent

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict:
        """Convert settings to dictionary."""
        return self.model_dump()

    def __str__(self) -> str:
        """String representation with sensitive fields masked."""
        settings_dict = self.to_dict()
        # Mask sensitive values
        if "openai_api_key" in settings_dict:
            settings_dict["openai_api_key"] = "***MASKED***"
        return f"Settings({settings_dict})"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    This is a singleton pattern to avoid reloading settings multiple times.
    The cache is cleared only when the Python process restarts.

    Returns:
        Settings: Application settings instance
    """
    settings = Settings()
    settings.ensure_directories()
    return settings
