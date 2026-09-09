"""Search query generation / regeneration node."""

from __future__ import annotations

import logging
from typing import Any

from ...config.settings import get_settings
from ...core.llm_factory import create_llm
from ...utils.parsers import extract_json_from_response
from ..prompts import SEARCH_QUERY_PROMPT, SEARCH_QUERY_REGENERATION_PROMPT
from ..state import ResearchGraphState

logger = logging.getLogger(__name__)


def _persona_fields(state: ResearchGraphState) -> dict[str, str]:
    persona = state.get("assistant_persona") or {}
    return {
        "assistant_persona": str(persona.get("persona") or "Research Analyst"),
        "assistant_expertise": str(
            persona.get("expertise") or "General research"
        ),
        "assistant_approach": str(
            persona.get("approach") or "Balanced factual synthesis"
        ),
    }


def _normalize_queries(raw: list[Any], user_question: str, num_queries: int) -> list[str]:
    queries: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            text = str(item.get("search_query") or item.get("query") or "").strip()
        else:
            text = str(item).strip()
        if text and text not in queries:
            queries.append(text)
        if len(queries) >= num_queries:
            break
    if not queries:
        queries = [user_question]
    return queries


def generate_search_queries_node(state: ResearchGraphState) -> dict[str, Any]:
    """Generate initial or regenerated search queries."""
    settings = get_settings()
    user_question = state["user_question"]
    retry_count = int(state.get("retry_count") or 0)
    prior = list(state.get("prior_search_queries") or [])
    current = list(state.get("search_queries") or [])

    # Fold the last batch into prior history when regenerating.
    if retry_count > 0 and current:
        for query in current:
            if query not in prior:
                prior.append(query)

    should_regen = bool(state.get("should_regenerate_queries"))
    search_quality = state.get("search_quality") or "ok"
    is_retry = retry_count > 0 or should_regen or search_quality != "ok"

    num_queries = settings.num_search_queries
    persona_fields = _persona_fields(state)
    llm = create_llm(settings=settings)
    relevance = state.get("relevance_evaluation") or {}

    if is_retry:
        logger.info(
            "Regenerating search queries (retry_count=%s, prior=%s)",
            retry_count,
            len(prior),
        )
        prompt = SEARCH_QUERY_REGENERATION_PROMPT.format(
            **persona_fields,
            user_question=user_question,
            retry_count=retry_count,
            previous_queries="; ".join(prior) if prior else "(none)",
            relevance_percentage=relevance.get("relevance_percentage", "n/a"),
            relevance_explanation=relevance.get("explanation", "n/a"),
            search_quality=search_quality,
            num_queries=num_queries,
        )
    else:
        logger.info("Generating initial search queries")
        prompt = SEARCH_QUERY_PROMPT.format(
            **persona_fields,
            user_question=user_question,
            num_queries=num_queries,
        )

    try:
        response = llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        payload = extract_json_from_response(str(text)) or {}
        queries = _normalize_queries(
            list(payload.get("queries") or []),
            user_question,
            num_queries,
        )
    except Exception as exc:
        logger.error("Query generation failed: %s", exc)
        queries = [user_question]

    if prior:
        filtered = [q for q in queries if q not in prior]
        if filtered:
            queries = filtered

    logger.info("Search queries: %s", queries)
    return {
        "search_queries": queries,
        "prior_search_queries": prior,
        "relevance_evaluation": None,
        "should_regenerate_queries": False,
        "search_results": [],
        "summaries": [],
        "passed_summaries": [],
        "scraped_content": [],
        "search_quality": "ok",
    }
