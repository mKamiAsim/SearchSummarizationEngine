"""LangGraph state schema for the research pipeline."""

from __future__ import annotations

from typing import Any, TypedDict


class ResearchGraphState(TypedDict, total=False):
    """Shared state passed between LangGraph nodes."""

    user_question: str

    assistant_persona: dict[str, Any] | None
    search_queries: list[str]
    prior_search_queries: list[str]
    search_results: list[dict[str, Any]]
    scraped_content: list[dict[str, Any]]
    summaries: list[dict[str, Any]]
    passed_summaries: list[dict[str, Any]]
    seen_urls: list[str]

    relevance_evaluation: dict[str, Any] | None
    should_regenerate_queries: bool
    search_quality: str
    retry_count: int
    max_retries: int

    report_mode: str
    markdown_report: str | None
    pdf_path: str | None
    markdown_path: str | None
    sources: list[str]
    save_to_file: str | None
    generate_pdf: bool

    errors: list[str]
    execution_time_ms: int


def initial_state(
    user_question: str,
    *,
    max_retries: int = 3,
    save_to_file: str | None = None,
    generate_pdf: bool = True,
) -> ResearchGraphState:
    """Build the starting graph state for a research run."""
    return ResearchGraphState(
        user_question=user_question.strip(),
        assistant_persona=None,
        search_queries=[],
        prior_search_queries=[],
        search_results=[],
        scraped_content=[],
        summaries=[],
        passed_summaries=[],
        seen_urls=[],
        relevance_evaluation=None,
        should_regenerate_queries=False,
        search_quality="ok",
        retry_count=0,
        max_retries=max_retries,
        report_mode="full",
        markdown_report=None,
        pdf_path=None,
        markdown_path=None,
        sources=[],
        save_to_file=save_to_file,
        generate_pdf=generate_pdf,
        errors=[],
        execution_time_ms=0,
    )
