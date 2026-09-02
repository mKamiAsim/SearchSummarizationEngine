"""
LLM factory module for creating and configuring language model instances.

This module provides a centralized way to instantiate LLMs with consistent
configuration across the application. It supports both local LM Studio
and cloud-based OpenAI-compatible endpoints.
"""

import logging
from functools import lru_cache
from langchain_openai import ChatOpenAI
from src.config.settings import Settings, get_settings
from pydantic import SecretStr

logger = logging.getLogger(__name__)


def create_llm(
    settings: Settings | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    model_name: str | None = None,
    streaming: bool = False,
) -> ChatOpenAI:
    """
    Create and configure a ChatOpenAI instance.

    This factory function creates LLM instances with proper configuration
    for both local (LM Studio) and cloud-based endpoints.

    Args:
        settings: Settings instance. If None, uses cached global settings.
        temperature: Override default temperature (0.0-1.0).
        max_tokens: Override default max tokens.
        model_name: Override default model name.
        streaming: Enable streaming responses.

    Returns:
        ChatOpenAI: Configured LLM instance

    Example:
        >>> llm = create_llm()
        >>> response = llm.invoke("Hello, world!")
        >>> print(response.content)
    """
    # Get settings
    if settings is None:
        settings = get_settings()

    # Use overrides or fall back to settings
    final_temperature = temperature if temperature is not None else settings.openai_temperature
    final_max_tokens = max_tokens if max_tokens is not None else settings.openai_max_tokens
    final_model_name = model_name if model_name is not None else settings.openai_model_name

    logger.info(
        "Creating LLM instance",
        extra={
            "model": final_model_name,
            "base_url": settings.openai_api_base,
            "temperature": final_temperature,
            "max_tokens": final_max_tokens,
            "streaming": streaming,
        },
    )

    # Create ChatOpenAI instance
    # Note: We use the OpenAI-compatible API, which works with LM Studio
    llm = ChatOpenAI(
        model=final_model_name,
        base_url=settings.openai_api_base,
        api_key=SecretStr(settings.openai_api_key),
        temperature=final_temperature,
        max_completion_tokens=final_max_tokens,
        streaming=streaming,
        timeout=settings.openai_timeout,
        # Disable built-in retries; we handle retries at the chain level
        max_retries=0,
    )

    logger.debug("LLM instance created successfully")

    return llm


@lru_cache(maxsize=1)
def get_cached_llm(
    temperature: float | None = None,
    max_tokens: int | None = None,
    model_name: str | None = None,
) -> ChatOpenAI:
    """
    Get a cached LLM instance for performance.

    This is useful when you need the same LLM configuration multiple times.
    The cache is keyed by the configuration parameters.

    Args:
        temperature: Temperature setting.
        max_tokens: Max tokens setting.
        model_name: Model name.

    Returns:
        ChatOpenAI: Cached LLM instance

    Note:
        The cache persists for the lifetime of the Python process.
        Use create_llm() if you need fresh instances.
    """
    return create_llm(
        temperature=temperature,
        max_tokens=max_tokens,
        model_name=model_name,
    )


def test_llm_connection(llm: ChatOpenAI | None = None) -> bool:
    """
    Test LLM connection with a simple query.

    This is useful for health checks and debugging connection issues.

    Args:
        llm: LLM instance to test. If None, creates a new one.

    Returns:
        bool: True if connection successful, False otherwise

    Example:
        >>> if test_llm_connection():
        ...     print("LLM is ready")
        ... else:
        ...     print("LLM connection failed")
    """
    if llm is None:
        llm = create_llm()

    try:
        logger.info("Testing LLM connection...")
        response = llm.invoke("Respond with just the word 'OK': What is 2+2?")

        if isinstance(response.content, str):
            text_content = response.content
        elif isinstance(response.content, list):
            # Join text strings, or extract text if they are content block dictionaries
            text_content = " ".join(
                [item if isinstance(item, str) else item.get(
                    "text", "") for item in response.content]
            )
        else:
            text_content = ""

        is_ok = "ok" in text_content.lower()
        logger.info(f"LLM connection test: {'PASSED' if is_ok else 'FAILED'}")
        return is_ok
    except Exception as e:
        logger.error(f"LLM connection test failed: {e}")
        return False


def get_llm_info(llm: ChatOpenAI) -> dict:
    """
    Get information about the LLM configuration.

    Args:
        llm: LLM instance to inspect.

    Returns:
        dict: Dictionary with LLM configuration details
    """
    return {
        "model": llm.model_name,
        "base_url": llm.client.base_url,
        "temperature": llm.temperature,
        "max_tokens": llm.max_tokens,
        "streaming": llm.streaming,
        "timeout": llm.request_timeout,
    }
