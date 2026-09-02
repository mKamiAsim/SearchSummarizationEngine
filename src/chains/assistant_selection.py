"""
Stage 1: Assistant Selection Chain.

Selects an appropriate expert persona based on the research question.
"""

import logging
from typing import Any

from langchain_core.runnables import Runnable

from config.settings import get_settings
from core.llm_factory import create_llm
from core.models import AssistantPersona
from prompts import get_assistant_selection_prompt
from utils.parsers import RobustPydanticParser

logger = logging.getLogger(__name__)


def create_assistant_selection_chain() -> Runnable:
    """
    Create the assistant selection chain using LCEL.

    Returns:
        Runnable: Chain that takes user_question and returns AssistantPersona

    Example:
        >>> chain = create_assistant_selection_chain()
        >>> result = chain.invoke({"user_question": "What is quantum computing?"})
        >>> print(result.persona)
    """
    settings = get_settings()

    # Load prompt template
    prompt = get_assistant_selection_prompt()

    # Create LLM
    llm = create_llm(settings=settings)

    # Create parser with fallback
    default_persona = AssistantPersona(
        persona="Research Analyst",
        expertise="General research and information synthesis",
        approach="Provide balanced, factual overview from multiple perspectives",
    )

    parser = RobustPydanticParser(
        model=AssistantPersona,
        default=default_persona,
        max_retries=settings.llm_retry_attempts,
    )

    # Build chain: prompt -> llm -> parser
    chain = prompt | llm | parser

    logger.debug("Created assistant selection chain")

    return chain


def select_assistant(user_question: str) -> AssistantPersona:
    """
    Select an appropriate assistant persona for the research question.

    Convenience function that creates and invokes the chain.

    Args:
        user_question: The research question

    Returns:
        AssistantPersona: Selected expert persona

    Example:
        >>> persona = select_assistant("What are the latest developments in AI?")
        >>> print(f"Persona: {persona.persona}")
    """
    logger.info(f"Selecting assistant persona for: '{user_question[:100]}...'")

    chain = create_assistant_selection_chain()
    result = chain.invoke({"user_question": user_question})

    logger.info(f"Selected persona: {result.persona}")

    return result
