"""Observability configuration for the research pipeline."""

import os

from ..config.settings import Settings


def configure_langsmith(settings: Settings) -> None:
    """Configure LangChain's standard LangSmith tracing environment variables."""
    os.environ["LANGCHAIN_TRACING_V2"] = str(
        settings.langchain_tracing_v2).lower()
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint

    if settings.langchain_api_key:
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
