"""Unit tests for LangGraph conditional routing."""

from src.graph.routing import route_after_relevance, route_after_search


def test_route_after_search_ok_goes_to_scrape():
    state = {
        "search_quality": "ok",
        "search_results": [{"url": "https://example.com"}],
        "retry_count": 0,
        "max_retries": 3,
    }
    assert route_after_search(state) == "scrape_and_summarize"


def test_route_after_search_insufficient_retries_left():
    state = {
        "search_quality": "insufficient",
        "search_results": [],
        "retry_count": 1,
        "max_retries": 3,
    }
    assert route_after_search(state) == "generate_search_queries"


def test_route_after_search_insufficient_retries_exhausted():
    state = {
        "search_quality": "insufficient",
        "search_results": [],
        "retry_count": 3,
        "max_retries": 3,
    }
    assert route_after_search(state) == "generate_reports"


def test_route_after_relevance_regenerate():
    state = {
        "should_regenerate_queries": True,
        "retry_count": 1,
        "max_retries": 3,
    }
    assert route_after_relevance(state) == "generate_search_queries"


def test_route_after_relevance_proceed():
    state = {
        "should_regenerate_queries": False,
        "retry_count": 0,
        "max_retries": 3,
    }
    assert route_after_relevance(state) == "generate_reports"


def test_route_after_relevance_exhausted_goes_to_report():
    state = {
        "should_regenerate_queries": True,
        "retry_count": 3,
        "max_retries": 3,
    }
    assert route_after_relevance(state) == "generate_reports"
