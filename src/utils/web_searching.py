"""
Web searching utilities using DuckDuckGo.

This module provides a clean interface for executing web searches
and collecting result URLs with metadata.
"""

import logging
import time
from typing import Any

from duckduckgo_search import DDGS
from langsmith import traceable

from ..config.settings import Settings, get_settings
from ..core.models import SearchResult

logger = logging.getLogger(__name__)


@traceable(name="web_search", run_type="tool")
def search_web(
    query: str,
    num_results: int = 3,
    settings: Settings | None = None,
) -> list[SearchResult]:
    """
    Execute a DuckDuckGo web search and return results.

    Args:
        query: Search query string
        num_results: Number of results to return (default: 3)
        settings: Settings instance. If None, uses cached global settings.

    Returns:
        list[SearchResult]: List of search results with URL, title, snippet

    Raises:
        Exception: If search fails (logged and returns empty list in production)

    Example:
        >>> results = search_web("quantum computing latest developments", num_results=3)
        >>> for result in results:
        ...     print(f"{result.title}: {result.url}")
    """
    if settings is None:
        settings = get_settings()

    logger.info(
        f"Executing web search for: '{query}' (max {num_results} results)")

    try:
        # Initialize DuckDuckGo search
        with DDGS() as ddgs:
            # Execute search
            results_raw: list[dict[str, Any]] = ddgs.text(
                query,
                max_results=num_results,
            )

            if not results_raw:
                logger.warning(f"No results found for query: '{query}'")
                return []

            # Convert to SearchResult models
            results: list[SearchResult] = []
            for idx, raw in enumerate(results_raw, start=1):
                result = SearchResult(
                    url=raw.get("href", ""),
                    title=raw.get("title", ""),
                    snippet=raw.get("body", ""),
                    search_query=query,
                    rank=idx,
                )
                results.append(result)
                logger.debug(f"Result {idx}: {result.title[:50]}...")

            logger.info(f"Found {len(results)} results for query: '{query}'")
            return results

    except Exception as e:
        logger.error(
            f"Web search failed for query '{query}': {e}", exc_info=True)
        # Return empty list on failure - pipeline will continue with other queries
        return []


@traceable(name="search_multiple_queries", run_type="tool")
def search_multiple_queries(
    queries: list[str],
    results_per_query: int = 3,
    delay_between_queries: float = 1.0,
    settings: Settings | None = None,
) -> list[SearchResult]:
    """
    Execute multiple search queries and aggregate results.

    Args:
        queries: List of search queries
        results_per_query: Number of results per query
        delay_between_queries: Delay between queries to avoid rate limiting
        settings: Settings instance

    Returns:
        list[SearchResult]: Aggregated results from all queries

    Example:
        >>> queries = ["quantum computing 2024", "quantum supremacy latest"]
        >>> results = search_multiple_queries(queries, results_per_query=3)
    """
    if settings is None:
        settings = get_settings()

    all_results: list[SearchResult] = []

    for idx, query in enumerate(queries):
        logger.info(f"Search {idx + 1}/{len(queries)}: '{query}'")

        results = search_web(
            query, num_results=results_per_query, settings=settings)
        all_results.extend(results)

        # Add delay between queries to avoid rate limiting
        if idx < len(queries) - 1 and delay_between_queries > 0:
            logger.debug(
                f"Waiting {delay_between_queries}s before next query...")
            time.sleep(delay_between_queries)

    logger.info(
        f"Total results from {len(queries)} queries: {len(all_results)}")

    # Remove duplicates (by URL)
    seen_urls: set[str] = set()
    unique_results: list[SearchResult] = []
    for result in all_results:
        if result.url not in seen_urls:
            seen_urls.add(result.url)
            unique_results.append(result)

    if len(unique_results) < len(all_results):
        logger.info(
            f"Removed {len(all_results) - len(unique_results)} duplicate URLs"
        )

    return unique_results
