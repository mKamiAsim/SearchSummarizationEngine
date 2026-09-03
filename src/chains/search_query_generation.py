"""
Stage 2: Search Query Generation Chain.

Generates targeted search queries based on the selected persona and research question.
"""

import logging
from typing import Any

from langchain_core.runnables import Runnable

from ..config.settings import get_settings
from ..core.models import SearchQueryGeneration, AssistantPersona
from ..core.llm_factory import create_llm
from ..prompts import get_search_queries_prompt
from ..utils.parsers import RobustPydanticParser
from ..utils.time_context import get_time_context

logger = logging.getLogger(__name__)


def create_search_query_generation_chain() -> Runnable:
    """
    Create the search query generation chain using LCEL.

    Returns:
        Runnable: Chain that takes persona + question and returns SearchQueryGeneration

    Example:
        >>> chain = create_search_query_generation_chain()
        >>> result = chain.invoke({
        ...     "assistant_persona": "Quantum Computing Researcher",
        ...     "assistant_expertise": "Quantum algorithms...",
        ...     "assistant_approach": "Focus on recent breakthroughs...",
        ...     "user_question": "What is quantum supremacy?",
        ...     "num_queries": 2
        ... })
        >>> print(result.queries)
    """
    settings = get_settings()

    # Load prompt template
    prompt = get_search_queries_prompt()

    # Create LLM
    llm = create_llm(settings=settings)

    # Create parser with fallback
    default_queries = SearchQueryGeneration(
        queries=["default search query"],
        reasoning="Fallback queries due to parsing failure",
    )

    parser = RobustPydanticParser(
        model=SearchQueryGeneration,
        default=default_queries,
        max_retries=settings.llm_retry_attempts,
    )

    # Build chain: prompt -> llm -> parser
    chain = (prompt | llm | parser).with_config({
        "run_name": "Search Query Generation",
    })

    logger.debug("Created search query generation chain")

    return chain


def generate_search_queries(
    user_question: str,
    persona: AssistantPersona,
    num_queries: int | None = None,
) -> SearchQueryGeneration:
    """
    Generate targeted search queries for the research question.

    Convenience function that creates and invokes the chain.

    Args:
        user_question: The research question
        persona: Selected assistant persona
        num_queries: Number of queries to generate (default from settings)

    Returns:
        SearchQueryGeneration: Generated queries with reasoning

    Example:
        >>> persona = AssistantPersona(...)
        >>> result = generate_search_queries("What is quantum computing?", persona)
        >>> for query in result.queries:
        ...     print(f"- {query}")
    """
    settings = get_settings()

    if num_queries is None:
        num_queries = settings.num_search_queries

    logger.info(
        f"Generating {num_queries} search queries for: '{user_question[:100]}...'")

    chain = create_search_query_generation_chain()

    result = chain.invoke({
        "assistant_persona": persona.persona,
        "assistant_expertise": persona.expertise,
        "assistant_approach": persona.approach,
        "user_question": user_question,
        "num_queries": num_queries,
        **get_time_context(),
    })

    logger.info(f"Generated {len(result.queries)} queries: {result.queries}")

    return result
