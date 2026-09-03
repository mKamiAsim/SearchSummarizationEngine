from datetime import date

from src.prompts import (
    get_assistant_selection_prompt,
    get_report_compilation_prompt,
    get_search_queries_prompt,
    get_summarization_prompt,
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


def test_search_queries_prompt_keeps_product_names_and_current_year():
    prompt = get_search_queries_prompt()
    rendered = prompt.format(
        assistant_persona="Hardware Analyst",
        assistant_expertise="Workstation GPUs and Apple silicon",
        assistant_approach="Compare current hardware from sources",
        user_question="Compare Nvidia RTX Spark and Apple Mac Studio M5",
        num_queries=3,
        **get_time_context(today=date(2026, 9, 3)),
    )

    assert "Thursday" in rendered and "September 2026" in rendered
    assert "Do NOT replace unknown or new names" in rendered
    assert "Nvidia RTX Spark specs launch 2026" in rendered
    assert "Apple Mac Studio M5 review 2026" in rendered
    assert "2024" not in rendered
    assert "2025" not in rendered


def test_other_prompts_include_today_and_source_fidelity():
    ctx = get_time_context(today=date(2026, 9, 3))

    assistant = get_assistant_selection_prompt().format(
        user_question="What are the latest developments in quantum computing?",
        **ctx,
    )
    assert "September 2026" in assistant
    assert "2024-2025" not in assistant

    summary = get_summarization_prompt().format(
        user_question="Compare Nvidia RTX Spark and Apple Mac Studio M5",
        search_query="Nvidia RTX Spark specs launch 2026",
        web_page_content="Sample page",
        **ctx,
    )
    assert "Do not fill gaps with older products" in summary

    report = get_report_compilation_prompt().format(
        user_question="Compare Nvidia RTX Spark and Apple Mac Studio M5",
        assistant_persona="Hardware Analyst",
        assistant_expertise="GPUs",
        assistant_approach="Use current sources",
        all_summaries="Source 1: ...",
        **ctx,
    )
    assert "Do not replace the user's named products" in report
    assert "December 2024" not in report
