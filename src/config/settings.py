"""
Configuration management using pydantic-settings.

This module centralizes all configuration for the research engine,
including LLM endpoints, pipeline parameters, and logging settings.
All settings can be overridden via environment variables or .env file.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
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
        default=160,
        gt=0,
        description="Request timeout in seconds",
    )

    langchain_tracing_v2: bool = Field(
        default=True,
        validation_alias=AliasChoices("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2"),
        description="Enable LangSmith tracing when a LangSmith API key is configured",
    )

    langchain_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("LANGSMITH_API_KEY", "LANGCHAIN_API_KEY"),
        description="LangSmith API key",
    )

    langchain_project: str = Field(
        default="search-summarization-engine",
        validation_alias=AliasChoices("LANGSMITH_PROJECT", "LANGCHAIN_PROJECT"),
        description="LangSmith project name",
    )

    langchain_endpoint: str = Field(
        default="https://api.smith.langchain.com",
        validation_alias=AliasChoices("LANGSMITH_ENDPOINT", "LANGCHAIN_ENDPOINT"),
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

    max_relevance_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Max times to regenerate queries when relevance is below threshold",
    )

    search_retry_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Retry attempts per search query on empty/failed results",
    )

    search_retry_backoff: float = Field(
        default=1.5,
        gt=0.0,
        description="Backoff seconds multiplier between search retries",
    )

    relevance_pass_threshold_pct: float = Field(
        default=50.0,
        ge=0.0,
        le=100.0,
        description="Minimum percent of summaries that must pass relevance to write a full report",
    )

    relevance_llm_min_score: float = Field(
        default=3.5,
        ge=1.0,
        le=5.0,
        description="Minimum LLM relevance score (1-5) for a summary to pass",
    )

    relevance_embedding_min: float = Field(
        default=0.45,
        ge=0.0,
        le=1.0,
        description="Minimum embedding cosine similarity for a summary to pass",
    )

    embedding_backend: Literal["sentence_transformers"] = Field(
        default="sentence_transformers",
        description="Embedding backend for semantic relevance scoring",
    )

    embedding_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Hugging Face sentence-transformers model for embeddings",
    )

    generate_pdf: bool = Field(
        default=True,
        description="Also write a PDF report alongside Markdown (LangGraph path)",
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

    search_backend: Literal["auto", "tavily", "duckduckgo"] = Field(
        default="tavily",
        description=(
            "Web search provider. Default is Tavily (requires TAVILY_API_KEY). "
            "'auto' uses Tavily when a key is set, otherwise DuckDuckGo. "
            "DuckDuckGo's unofficial API often returns empty results."
        ),
    )

    tavily_api_key: str = Field(
        default="",
        description="Tavily API key (https://app.tavily.com). Required for reliable search.",
    )

    tavily_search_depth: Literal["basic", "advanced"] = Field(
        default="basic",
        description="Tavily search depth: basic (1 credit) or advanced (2 credits)",
    )

    scraper_timeout_seconds: int = Field(
        default=30,
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
        default=False,
        description="Include generated search queries in report metadata (not in report body)",
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
        for secret_field in ("openai_api_key", "tavily_api_key", "langchain_api_key"):
            if secret_field in settings_dict and settings_dict[secret_field]:
                settings_dict[secret_field] = "***MASKED***"
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
