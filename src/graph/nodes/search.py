"""Web search execution node with retries and URL deduplication."""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urlparse, urlunparse

from ...config.settings import get_settings
from ...utils.time_context import is_historical_query
from ...utils.web_searching import search_web
from ..state import ResearchGraphState

logger = logging.getLogger(__name__)


def canonicalize_url(url: str) -> str:
    """Normalize a URL for deduplication."""
    raw = (url or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
        scheme = (parsed.scheme or "https").lower()
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = parsed.path.rstrip("/") or ""
        return urlunparse((scheme, netloc, path, "", "", ""))
    except Exception:
        return raw.rstrip("/").lower()


def execute_web_search_node(state: ResearchGraphState) -> dict[str, Any]:
    """Execute searches with retry logic and cross-run URL deduplication."""
    settings = get_settings()
    queries = list(state.get("search_queries") or [])
    seen = set(state.get("seen_urls") or [])
    user_question = state["user_question"]
    historical = is_historical_query(user_question)
    timelimit = None if historical else "y"

    collected: list[dict[str, Any]] = []
    empty_or_failed = 0

    logger.info("Executing web search for %s queries", len(queries))

    for idx, query in enumerate(queries):
        results = []
        last_error: Exception | None = None
        for attempt in range(1, settings.search_retry_attempts + 1):
            try:
                results = search_web(
                    query,
                    num_results=settings.num_search_results_per_query,
                    settings=settings,
                    timelimit=timelimit,
                )
                if results:
                    break
                logger.warning(
                    "Empty results for '%s' (attempt %s/%s)",
                    query,
                    attempt,
                    settings.search_retry_attempts,
                )
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Search failed for '%s' (attempt %s/%s): %s",
                    query,
                    attempt,
                    settings.search_retry_attempts,
                    exc,
                )
            if attempt < settings.search_retry_attempts:
                time.sleep(settings.search_retry_backoff * attempt)

        if not results:
            empty_or_failed += 1
            if last_error:
                logger.error("Giving up on query '%s': %s", query, last_error)
            continue

        for result in results:
            canonical = canonicalize_url(result.url)
            if not canonical or canonical in seen:
                continue
            seen.add(canonical)
            collected.append(
                {
                    "url": result.url,
                    "canonical_url": canonical,
                    "title": result.title,
                    "snippet": result.snippet,
                    "search_query": result.search_query,
                    "rank": result.rank,
                }
            )

        if idx < len(queries) - 1 and settings.search_delay_seconds > 0:
            time.sleep(settings.search_delay_seconds)

    # Quality gate: all queries empty, or fewer unique URLs than queries.
    if not collected or empty_or_failed == len(queries):
        quality = "insufficient"
        retry_count = int(state.get("retry_count") or 0) + 1
        logger.warning(
            "Search quality insufficient (unique=%s, empty_queries=%s). retry→%s",
            len(collected),
            empty_or_failed,
            retry_count,
        )
        return {
            "search_results": collected,
            "seen_urls": list(seen),
            "search_quality": quality,
            "retry_count": retry_count,
            "should_regenerate_queries": True,
        }

    # Sparse but non-empty results are usable; proceed to scrape.
    logger.info("Search produced %s unique URLs", len(collected))
    return {
        "search_results": collected,
        "seen_urls": list(seen),
        "search_quality": "ok",
        "should_regenerate_queries": False,
    }
