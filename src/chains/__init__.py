"""Chains module implementing the 5-stage research pipeline."""

from chains.assistant_selection import create_assistant_selection_chain, select_assistant
from chains.search_query_generation import create_search_query_generation_chain, generate_search_queries
from chains.content_summarization import create_summarization_chain, summarize_content
from chains.report_compilation import create_report_compilation_chain, compile_report, format_summaries_for_compilation

__all__ = [
    "create_assistant_selection_chain",
    "select_assistant",
    "create_search_query_generation_chain",
    "generate_search_queries",
    "create_summarization_chain",
    "summarize_content",
    "create_report_compilation_chain",
    "compile_report",
    "format_summaries_for_compilation",
]
