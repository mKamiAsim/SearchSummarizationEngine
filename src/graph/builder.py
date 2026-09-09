"""Compile the LangGraph research StateGraph (Chapter 5 pattern)."""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from .nodes import (
    assess_relevance_node,
    execute_web_search_node,
    generate_reports_node,
    generate_search_queries_node,
    persist_outputs_node,
    scrape_and_summarize_node,
    select_assistant_node,
)
from .routing import route_after_relevance, route_after_search
from .state import ResearchGraphState


def build_research_graph() -> StateGraph:
    """Construct the research StateGraph with relevance-gated routing."""
    graph = StateGraph(ResearchGraphState)

    graph.add_node("select_assistant", select_assistant_node)
    graph.add_node("generate_search_queries", generate_search_queries_node)
    graph.add_node("execute_web_search", execute_web_search_node)
    graph.add_node("scrape_and_summarize", scrape_and_summarize_node)
    graph.add_node("assess_relevance", assess_relevance_node)
    graph.add_node("generate_reports", generate_reports_node)
    graph.add_node("persist_outputs", persist_outputs_node)

    graph.add_edge(START, "select_assistant")
    graph.add_edge("select_assistant", "generate_search_queries")
    graph.add_edge("generate_search_queries", "execute_web_search")

    graph.add_conditional_edges(
        "execute_web_search",
        route_after_search,
        {
            "scrape_and_summarize": "scrape_and_summarize",
            "generate_search_queries": "generate_search_queries",
            "generate_reports": "generate_reports",
        },
    )

    graph.add_edge("scrape_and_summarize", "assess_relevance")

    graph.add_conditional_edges(
        "assess_relevance",
        route_after_relevance,
        {
            "generate_search_queries": "generate_search_queries",
            "generate_reports": "generate_reports",
        },
    )

    graph.add_edge("generate_reports", "persist_outputs")
    graph.add_edge("persist_outputs", END)

    return graph


@lru_cache(maxsize=1)
def get_compiled_graph():
    """Return a cached compiled graph application."""
    return build_research_graph().compile()
