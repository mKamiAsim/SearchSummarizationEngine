"""Scrape and summarize node."""

from __future__ import annotations

import logging
from typing import Any

from ...config.settings import get_settings
from ...core.llm_factory import create_llm
from ...core.models import ScrapedContent
from ...utils.parsers import extract_json_from_response
from ...utils.web_scraping import scrape_urls
from ..prompts import SUMMARIZATION_PROMPT
from ..state import ResearchGraphState

logger = logging.getLogger(__name__)


def scrape_and_summarize_node(state: ResearchGraphState) -> dict[str, Any]:
    """Scrape search result URLs and summarize each page."""
    settings = get_settings()
    user_question = state["user_question"]
    search_results = list(state.get("search_results") or [])
    urls = [r["url"] for r in search_results if r.get("url")]

    if not urls:
        logger.warning("No URLs to scrape")
        return {
            "scraped_content": [],
            "summaries": [],
        }

    scraped_models = scrape_urls(
        urls,
        max_characters_per_url=settings.result_text_max_characters,
    )
    scraped_content = [
        s.model_dump() if isinstance(s, ScrapedContent) else dict(s)
        for s in scraped_models
    ]

    query_by_url = {
        r["url"]: r.get("search_query", "") for r in search_results if r.get("url")
    }
    llm = create_llm(settings=settings)
    summaries: list[dict[str, Any]] = []

    for scraped in scraped_content:
        url = str(scraped.get("url") or "")
        content = str(scraped.get("content") or "")
        success = bool(scraped.get("success", True))
        if not success or len(content.strip()) < 50:
            logger.info("Skipping weak scrape: %s", url)
            continue

        search_query = query_by_url.get(url, "")
        prompt = SUMMARIZATION_PROMPT.format(
            user_question=user_question,
            search_query=search_query,
            web_page_content=content[: settings.result_text_max_characters],
        )
        try:
            response = llm.invoke(prompt)
            text = response.content if hasattr(response, "content") else str(response)
            payload = extract_json_from_response(str(text)) or {}
            summaries.append(
                {
                    "url": url,
                    "title": scraped.get("title") or "",
                    "summary": str(payload.get("summary") or "").strip()
                    or "No summary produced.",
                    "key_points": list(payload.get("key_points") or []),
                    "relevance_score": int(payload.get("relevance_score") or 50),
                    "source_type": str(payload.get("source_type") or "web"),
                    "credibility_notes": str(payload.get("credibility_notes") or ""),
                    "query_components_addressed": list(
                        payload.get("query_components_addressed") or []
                    ),
                    "search_query": search_query,
                    "user_question": user_question,
                }
            )
        except Exception as exc:
            logger.warning("Summarization failed for %s: %s", url, exc)
            continue

    logger.info("Summarized %s sources", len(summaries))
    return {
        "scraped_content": scraped_content,
        "summaries": summaries,
    }
