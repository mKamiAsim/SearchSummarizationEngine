"""Observability configuration for the research pipeline."""

import os

from ..config.settings import Settings


def configure_langsmith(settings: Settings) -> None:
    """Configure LangSmith tracing environment variables used by LangGraph."""
    enabled = bool(settings.langchain_tracing_v2 and settings.langchain_api_key)
    os.environ["LANGSMITH_TRACING"] = "true" if enabled else "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "true" if enabled else "false"
    os.environ["LANGSMITH_PROJECT"] = settings.langchain_project
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    os.environ["LANGSMITH_ENDPOINT"] = settings.langchain_endpoint
    os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint

    if settings.langchain_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    else:
        os.environ.pop("LANGSMITH_API_KEY", None)
        os.environ.pop("LANGCHAIN_API_KEY", None)
