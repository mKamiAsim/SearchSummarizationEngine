"""Conditional edge routers for the research StateGraph."""

from __future__ import annotations

from typing import Literal

from .state import ResearchGraphState

AfterSearchRoute = Literal[
    "scrape_and_summarize",
    "generate_search_queries",
    "generate_reports",
]
AfterRelevanceRoute = Literal["generate_search_queries", "generate_reports"]
AfterCritiqueRoute = Literal["revise_report", "persist_outputs"]


def _retries_remaining(state: ResearchGraphState) -> bool:
    retry_count = int(state.get("retry_count") or 0)
    max_retries = int(state.get("max_retries") or 3)
    return retry_count < max_retries


def route_after_search(state: ResearchGraphState) -> AfterSearchRoute:
    """Route after web search based on result quality and retry budget."""
    quality = (state.get("search_quality") or "ok").lower()
    results = state.get("search_results") or []

    if quality == "ok" and results:
        return "scrape_and_summarize"

    if _retries_remaining(state):
        return "generate_search_queries"

    # Exhausted retries with empty/poor search — caution report path.
    return "generate_reports"


def route_after_relevance(state: ResearchGraphState) -> AfterRelevanceRoute:
    """Route after relevance assessment using the 50% gate and retry counter."""
    if state.get("should_regenerate_queries") and _retries_remaining(state):
        return "generate_search_queries"
    return "generate_reports"


def route_after_critique(state: ResearchGraphState) -> AfterCritiqueRoute:
    """Revise only on material defects and only within the revision budget."""
    critique = state.get("report_critique") or {}
    revision_count = int(state.get("revision_count") or 0)
    max_revisions = int(state.get("max_report_revisions") or 0)
    if critique.get("decision") == "revise" and revision_count < max_revisions:
        return "revise_report"
    return "persist_outputs"
