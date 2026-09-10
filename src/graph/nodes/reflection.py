"""Report critic and revision nodes for the bounded Reflexion loop."""

from __future__ import annotations

import logging
from typing import Any

from ...config.settings import get_settings
from ...core.llm_factory import create_llm
from ...utils.parsers import extract_json_from_response
from ..prompts import REPORT_CRITIQUE_PROMPT, REPORT_REVISION_PROMPT
from ..state import ResearchGraphState

logger = logging.getLogger(__name__)


def _format_summaries(summaries: list[dict[str, Any]]) -> str:
    return "\n\n".join(
        f"Source [{idx}]: {summary.get('url', '')}\n{summary.get('summary', '')}"
        for idx, summary in enumerate(summaries, start=1)
    ) or "(No evidence supplied.)"


def _format_components(components: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"- {item.get('name', '')}" for item in components
    ) or "- Full research question"


def critique_report_node(state: ResearchGraphState) -> dict[str, Any]:
    """Review the draft for evidence, coverage, and query-appropriate structure."""
    settings = get_settings()
    llm = create_llm(settings=settings, temperature=0.0)
    prompt = REPORT_CRITIQUE_PROMPT.format(
        user_question=state["user_question"],
        research_components=_format_components(
            list(state.get("research_components") or [])
        ),
        all_summaries=_format_summaries(list(state.get("passed_summaries") or [])),
        draft_report=state.get("draft_report") or state.get("markdown_report") or "",
    )
    default = {
        "decision": "accept",
        "missing_components": [],
        "unsupported_claims": [],
        "citation_problems": [],
        "unnecessary_sections": [],
        "required_changes": [],
        "explanation": "Critique unavailable; preserving the draft.",
    }
    try:
        response = llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        critique = {**default, **(extract_json_from_response(str(text)) or {})}
    except Exception as exc:
        logger.warning("Report critique failed: %s", exc)
        critique = default
    return {"report_critique": critique}


def revise_report_node(state: ResearchGraphState) -> dict[str, Any]:
    """Revise the report once using structured critic feedback."""
    settings = get_settings()
    llm = create_llm(settings=settings)
    prompt = REPORT_REVISION_PROMPT.format(
        user_question=state["user_question"],
        all_summaries=_format_summaries(list(state.get("passed_summaries") or [])),
        draft_report=state.get("draft_report") or state.get("markdown_report") or "",
        critique=state.get("report_critique") or {},
    )
    draft = state.get("draft_report") or state.get("markdown_report") or ""
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        draft = str(content).strip() or draft
    except Exception as exc:
        logger.warning("Report revision failed: %s", exc)
    return {
        "draft_report": draft,
        "markdown_report": draft,
        "revision_count": int(state.get("revision_count") or 0) + 1,
    }
