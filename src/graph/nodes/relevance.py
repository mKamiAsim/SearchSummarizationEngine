"""Relevance assessment node."""

from __future__ import annotations

import logging
from typing import Any

from ...config.settings import get_settings
from ..scoring import score_summaries
from ..state import ResearchGraphState

logger = logging.getLogger(__name__)


def assess_relevance_node(state: ResearchGraphState) -> dict[str, Any]:
    """Evaluate summary relevance and decide whether to regenerate queries."""
    settings = get_settings()
    summaries = list(state.get("summaries") or [])
    user_question = state["user_question"]

    evaluation = score_summaries(
        user_question=user_question,
        summaries=summaries,
        settings=settings,
    )
    passed = list(evaluation.get("passed_summaries") or [])
    relevance_pct = float(evaluation.get("relevance_percentage") or 0.0)
    threshold = float(settings.relevance_pass_threshold_pct)

    should_regenerate = relevance_pct < threshold
    updates: dict[str, Any] = {
        "relevance_evaluation": {
            "relevance_percentage": relevance_pct,
            "relevant_count": evaluation.get("relevant_count", 0),
            "total_count": evaluation.get("total_count", 0),
            "per_summary": evaluation.get("per_summary", []),
            "query_components": evaluation.get("query_components", []),
            "explanation": evaluation.get("explanation", ""),
            "coverage_gaps": evaluation.get("coverage_gaps", []),
        },
        "passed_summaries": passed,
        "should_regenerate_queries": should_regenerate,
        "report_mode": "full" if not should_regenerate else "insufficient_sources",
    }

    if should_regenerate:
        retry_count = int(state.get("retry_count") or 0) + 1
        updates["retry_count"] = retry_count
        logger.info(
            "Relevance %.1f%% < %.1f%% — regenerate (retry→%s)",
            relevance_pct,
            threshold,
            retry_count,
        )
    else:
        logger.info(
            "Relevance %.1f%% >= %.1f%% — proceed to report (%s passed)",
            relevance_pct,
            threshold,
            len(passed),
        )
        updates["report_mode"] = "full"

    return updates
