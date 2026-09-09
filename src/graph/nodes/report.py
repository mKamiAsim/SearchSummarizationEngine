"""Report generation node (Markdown synthesis for full / caution modes)."""

from __future__ import annotations

import logging
import re
from typing import Any

from ...config.settings import get_settings
from ...core.llm_factory import create_llm
from ...utils.time_context import is_historical_query
from ..prompts import FULL_REPORT_PROMPT, INSUFFICIENT_REPORT_PROMPT
from ..state import ResearchGraphState

logger = logging.getLogger(__name__)


def needs_temporal_context(user_question: str) -> bool:
    """True when the question explicitly asks for time-bounded information."""
    if is_historical_query(user_question):
        return True
    return bool(
        re.search(
            r"\b(latest|current|recent|this year|today|202\d|announced|released)\b",
            user_question,
            re.IGNORECASE,
        )
    )


def _format_summaries(summaries: list[dict[str, Any]]) -> str:
    if not summaries:
        return "(No relevance-passed sources available.)"
    parts: list[str] = []
    for idx, summary in enumerate(summaries, start=1):
        key_points = summary.get("key_points") or []
        points = "\n".join(f"  - {p}" for p in key_points) if key_points else "  - (none)"
        parts.append(
            "\n".join(
                [
                    f"Source [{idx}]:",
                    f"URL: {summary.get('url', '')}",
                    f"Summary: {summary.get('summary', '')}",
                    f"Key Points:\n{points}",
                ]
            )
        )
    return "\n\n".join(parts)


def _persona_fields(state: ResearchGraphState) -> dict[str, str]:
    persona = state.get("assistant_persona") or {}
    return {
        "assistant_persona": str(persona.get("persona") or "Research Analyst"),
        "assistant_expertise": str(
            persona.get("expertise") or "General research"
        ),
        "assistant_approach": str(
            persona.get("approach") or "Balanced factual synthesis"
        ),
    }


def generate_reports_node(state: ResearchGraphState) -> dict[str, Any]:
    """Generate Markdown report content in full or insufficient-sources mode."""
    settings = get_settings()
    user_question = state["user_question"]
    passed = list(state.get("passed_summaries") or [])
    relevance = state.get("relevance_evaluation") or {}
    search_quality = (state.get("search_quality") or "ok").lower()

    # Force caution mode when evidence is too weak.
    relevance_pct = float(relevance.get("relevance_percentage") or 0.0)
    threshold = float(settings.relevance_pass_threshold_pct)
    if (
        not passed
        or search_quality != "ok"
        or relevance_pct < threshold
        or state.get("report_mode") == "insufficient_sources"
    ):
        report_mode = "insufficient_sources"
    else:
        report_mode = "full"

    temporal = "yes" if needs_temporal_context(user_question) else "no"
    summaries_text = _format_summaries(passed)
    coverage_gaps = relevance.get("coverage_gaps") or []
    if not coverage_gaps and report_mode == "insufficient_sources":
        coverage_gaps = relevance.get("query_components") or [user_question]

    llm = create_llm(settings=settings)
    persona_fields = _persona_fields(state)

    if report_mode == "full":
        logger.info("Generating full Markdown report from %s sources", len(passed))
        prompt = FULL_REPORT_PROMPT.format(
            user_question=user_question,
            **persona_fields,
            all_summaries=summaries_text,
            needs_temporal_context=temporal,
        )
    else:
        logger.info(
            "Generating caution / insufficient-sources report (passed=%s)",
            len(passed),
        )
        prompt = INSUFFICIENT_REPORT_PROMPT.format(
            user_question=user_question,
            **persona_fields,
            all_summaries=summaries_text,
            coverage_gaps="\n".join(f"- {g}" for g in coverage_gaps) or "- Insufficient evidence overall",
            needs_temporal_context=temporal,
        )

    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        markdown = str(content).strip()
    except Exception as exc:
        logger.error("Report generation failed: %s", exc)
        markdown = (
            f"# Research Report\n\n"
            f"## Caution\n\n"
            f"Relevant sources were insufficient to produce a high-confidence report, "
            f"and report generation encountered an error.\n\n"
            f"## Research Question\n\n{user_question}\n\n"
            f"## Limited Findings\n\nNo reliable findings could be produced.\n"
        )
        report_mode = "insufficient_sources"

    sources = [str(s.get("url")) for s in passed if s.get("url")]
    return {
        "markdown_report": markdown,
        "sources": sources,
        "report_mode": report_mode,
        "passed_summaries": passed,
    }
