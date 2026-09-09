from datetime import date

from src.graph.prompts import (
    ASSISTANT_SELECTION_PROMPT,
    FULL_REPORT_PROMPT,
    SEARCH_QUERY_PROMPT,
    SUMMARIZATION_PROMPT,
)
from src.utils.time_context import get_time_context, is_historical_query


def test_time_context_uses_injected_date():
    ctx = get_time_context(today=date(2026, 9, 3))
    assert ctx["current_year"] == "2026"
    assert "3 September 2026" in ctx["current_date"] or "03 September 2026" in ctx["current_date"]


def test_latest_product_question_is_not_historical():
    assert not is_historical_query(
        "Compare Nvidia RTX Spark and Apple Mac Studio M5",
        today=date(2026, 9, 3),
    )


def test_explicit_past_year_is_historical():
    assert is_historical_query("Mac Studio in 2024", today=date(2026, 9, 3))


def test_history_language_is_historical():
    assert is_historical_query(
        "evolution of transformer architectures",
        today=date(2026, 9, 3),
    )


def test_current_year_in_question_is_not_historical():
    assert not is_historical_query(
        "Nvidia RTX Spark launch 2026",
        today=date(2026, 9, 3),
    )


def test_search_query_prompt_preserves_placeholders():
    rendered = SEARCH_QUERY_PROMPT.format(
        assistant_persona="Hardware Analyst",
        assistant_expertise="Workstation GPUs and Apple silicon",
        assistant_approach="Compare current hardware from sources",
        user_question="Compare Nvidia RTX Spark and Apple Mac Studio M5",
        num_queries=3,
    )
    assert "Nvidia RTX Spark" in rendered
    assert "Apple Mac Studio M5" in rendered
    assert "EXACTLY from the research question" in rendered


def test_other_prompts_are_role_instructed():
    assistant = ASSISTANT_SELECTION_PROMPT.format(
        user_question="What are the latest developments in quantum computing?",
    )
    assert "expert persona" in assistant.lower() or "expert analyst" in assistant.lower()

    summary = SUMMARIZATION_PROMPT.format(
        user_question="Compare Nvidia RTX Spark and Apple Mac Studio M5",
        search_query="Nvidia RTX Spark specs",
        web_page_content="Sample page",
    )
    assert "ONLY facts present in the source text" in summary

    report = FULL_REPORT_PROMPT.format(
        user_question="Compare Nvidia RTX Spark and Apple Mac Studio M5",
        assistant_persona="Hardware Analyst",
        assistant_expertise="GPUs",
        assistant_approach="Use current sources",
        all_summaries="Source 1: ...",
        needs_temporal_context="no",
    )
    assert "Do NOT invent facts" in report
