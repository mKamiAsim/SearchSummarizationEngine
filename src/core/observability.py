"""Observability configuration for the research pipeline."""

import os

from ..config.settings import Settings


def configure_langsmith(settings: Settings) -> None:
    """Configure LangSmith tracing environment variables used by LangGraph."""
    enabled = bool(settings.langchain_tracing_v2 and settings.langchain_api_key)
    os.environ["LANGCHAIN_TRACING_V2"] = "true" if enabled else "false"
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint

    if settings.langchain_api_key:
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    elif not enabled:
        os.environ.pop("LANGCHAIN_API_KEY", None)
