"""
Web searching utilities.

Tavily is the primary provider. DuckDuckGo's unofficial API is kept as a
fallback, but it frequently returns empty result lists with no exception.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from duckduckgo_search import DDGS
from langsmith import traceable

from ..config.settings import Settings, get_settings
from ..core.models import SearchResult
from .time_context import is_historical_query

logger = logging.getLogger(__name__)

_TIMELIMIT_TO_TAVILY = {
    "d": "day",
    "w": "week",
    "m": "month",
    "y": "year",
    "day": "day",
    "week": "week",
    "month": "month",
    "year": "year",
}


def _without_settings(inputs: dict[str, Any]) -> dict[str, Any]:
    """Drop Settings objects so API keys are not written to LangSmith traces."""
    return {key: value for key, value in inputs.items() if key != "settings"}


def resolve_search_backend(settings: Settings) -> str:
    """Return the provider name that will actually be used."""
    if settings.search_backend == "auto":
        return "tavily" if settings.tavily_api_key.strip() else "duckduckgo"
    return settings.search_backend


def _search_tavily(
    query: str,
    num_results: int,
    timelimit: str | None,
    settings: Settings,
) -> list[SearchResult]:
    if not settings.tavily_api_key.strip():
        raise ValueError(
            "Tavily search requires TAVILY_API_KEY. Create a key at "
            "https://app.tavily.com and add it to your .env file."
        )

    from tavily import TavilyClient

    client = TavilyClient(api_key=settings.tavily_api_key)
    search_kwargs: dict[str, Any] = {
        "query": query,
        "max_results": num_results,
        "search_depth": settings.tavily_search_depth,
    }
    if timelimit:
        search_kwargs["time_range"] = _TIMELIMIT_TO_TAVILY.get(timelimit, "year")

    payload = client.search(**search_kwargs)
    raw_results = payload.get("results") or []

    results: list[SearchResult] = []
    for idx, item in enumerate(raw_results, start=1):
        url = (item.get("url") or "").strip()
        if not url:
            continue
        results.append(
            SearchResult(
                url=url,
                title=item.get("title") or "",
                snippet=item.get("content") or "",
                search_query=query,
                rank=idx,
            )
        )
    return results


def _search_duckduckgo(
    query: str,
    num_results: int,
    timelimit: str | None,
) -> list[SearchResult]:
    with DDGS() as ddgs:
        search_kwargs: dict[str, Any] = {"max_results": num_results}
        if timelimit:
            search_kwargs["timelimit"] = timelimit

        results_raw: list[dict[str, Any]] = ddgs.text(query, **search_kwargs) or []

    results: list[SearchResult] = []
    for idx, raw in enumerate(results_raw, start=1):
        url = raw.get("href") or raw.get("url") or ""
        if not url:
            continue
        results.append(
            SearchResult(
                url=url,
                title=raw.get("title", ""),
                snippet=raw.get("body", ""),
                search_query=query,
                rank=idx,
            )
        )
    return results


@traceable(
    name="web_search",
    run_type="tool",
    process_inputs=_without_settings,
)
def search_web(
    query: str,
    num_results: int = 3,
    settings: Settings | None = None,
    timelimit: str | None = "y",
) -> list[SearchResult]:
    """
    Execute a web search and return results.

    Uses Tavily when configured; otherwise DuckDuckGo. Empty DuckDuckGo
    responses are treated as a backend failure, not as "no documents exist".

    Args:
        query: Search query string
        num_results: Number of results to return (default: 3)
        settings: Settings instance. If None, uses cached global settings.
        timelimit: Recency filter: d/w/m/y, or None for all time.

    Returns:
        list[SearchResult]: List of search results with URL, title, snippet
    """
    if settings is None:
        settings = get_settings()

    backend = resolve_search_backend(settings)
    logger.info(
        f"Executing {backend} search for: '{query}' (max {num_results} results"
        f"{', timelimit=' + str(timelimit) if timelimit else ', all-time'})"
    )

    try:
        if backend == "tavily":
            results = _search_tavily(query, num_results, timelimit, settings)
        else:
            results = _search_duckduckgo(query, num_results, timelimit)
    except ValueError:
        raise
    except Exception as exc:
        logger.error(
            f"{backend} search failed for query '{query}': {exc}",
            exc_info=True,
        )
        if backend == "tavily" and settings.search_backend == "auto":
            logger.warning("Falling back to DuckDuckGo after Tavily failure")
            try:
                results = _search_duckduckgo(query, num_results, timelimit)
            except Exception as fallback_exc:
                logger.error(
                    f"DuckDuckGo fallback failed for query '{query}': {fallback_exc}",
                    exc_info=True,
                )
                return []
        else:
            return []

    if not results:
        logger.warning(f"No results found for query: '{query}' via {backend}")
        if backend == "duckduckgo":
            logger.warning(
                "DuckDuckGo often returns empty lists due to rate limits. "
                "Set TAVILY_API_KEY in .env to use Tavily search."
            )
        return []

    for idx, result in enumerate(results, start=1):
        logger.debug(f"Result {idx}: {result.title[:50]}...")

    logger.info(f"Found {len(results)} results for query: '{query}' via {backend}")
    return results


@traceable(
    name="search_multiple_queries",
    run_type="tool",
    process_inputs=_without_settings,
)
def search_multiple_queries(
    queries: list[str],
    results_per_query: int = 3,
    delay_between_queries: float = 1.0,
    settings: Settings | None = None,
    user_question: str | None = None,
) -> list[SearchResult]:
    """
    Execute multiple search queries and aggregate results.

    Args:
        queries: List of search queries
        results_per_query: Number of results per query
        delay_between_queries: Delay between queries to avoid rate limiting
        settings: Settings instance
        user_question: Original question. Used to skip the past-year filter
            when the user explicitly asked for a historical period.

    Returns:
        list[SearchResult]: Aggregated results from all queries
    """
    if settings is None:
        settings = get_settings()

    historical = is_historical_query(user_question or "")
    timelimit = None if historical else "y"
    if historical:
        logger.info(
            "Historical question detected — searching all time, no recency filter"
        )

    all_results: list[SearchResult] = []

    for idx, query in enumerate(queries):
        logger.info(f"Search {idx + 1}/{len(queries)}: '{query}'")

        results = search_web(
            query,
            num_results=results_per_query,
            settings=settings,
            timelimit=timelimit,
        )
        all_results.extend(results)

        if idx < len(queries) - 1 and delay_between_queries > 0:
            logger.debug(
                f"Waiting {delay_between_queries}s before next query..."
            )
            time.sleep(delay_between_queries)

    logger.info(
        f"Total results from {len(queries)} queries: {len(all_results)}"
    )

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
