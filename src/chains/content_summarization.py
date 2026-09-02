"""
Stage 4: Content Summarization Chain.

Summarizes individual scraped web page content in context of the research question.
"""

import logging

from langchain_core.runnables import Runnable

from src.config.settings import get_settings
from src.core.llm_factory import create_llm
from src.core.models import SummarizedResult, ScrapedContent
from src.prompts import get_summarization_prompt
from src.utils.parsers import RobustPydanticParser

logger = logging.getLogger(__name__)


def create_summarization_chain() -> Runnable:
    """
    Create the content summarization chain using LCEL.
    
    Returns:
        Runnable: Chain that takes scraped content + context and returns SummarizedResult
    
    Example:
        >>> chain = create_summarization_chain()
        >>> result = chain.invoke({
        ...     "user_question": "What is quantum computing?",
        ...     "search_query": "quantum computing basics",
        ...     "web_page_content": "Quantum computing uses quantum mechanics..."
        ... })
        >>> print(result.summary)
    """
    settings = get_settings()
    
    # Load prompt template
    prompt = get_summarization_prompt()
    
    # Create LLM
    llm = create_llm(settings=settings)
    
    # Create parser with fallback
    default_summary = SummarizedResult(
        url="",
        summary="Failed to summarize content",
        search_query="",
        user_question="",
        key_points=["Content summarization failed"],
        relevance_score=0,
    )
    
    parser = RobustPydanticParser(
        model=SummarizedResult,
        default=default_summary,
        max_retries=settings.llm_retry_attempts,
    )
    
    # Build chain: prompt -> llm -> parser
    chain = prompt | llm | parser
    
    logger.debug("Created summarization chain")
    
    return chain


def summarize_content(
    scraped_content: ScrapedContent,
    user_question: str,
    search_query: str,
) -> SummarizedResult:
    """
    Summarize a single scraped web page.
    
    Convenience function that creates and invokes the chain.
    
    Args:
        scraped_content: Scraped content from web page
        user_question: Original research question
        search_query: Search query that found this page
    
    Returns:
        SummarizedResult: Summary with key points and relevance score
    
    Example:
        >>> scraped = ScrapedContent(url="https://...", content="...", success=True)
        >>> summary = summarize_content(scraped, "What is AI?", "AI basics")
        >>> print(summary.summary)
    """
    settings = get_settings()
    
    if not scraped_content.success:
        logger.warning(f"Skipping summarization for failed scrape: {scraped_content.url}")
        return SummarizedResult(
            url=scraped_content.url,
            summary=f"Failed to scrape content: {scraped_content.error_message}",
            search_query=search_query,
            user_question=user_question,
            key_points=[],
            relevance_score=0,
        )
    
    if len(scraped_content.content.strip()) == 0:
        logger.warning(f"Skipping summarization for empty content: {scraped_content.url}")
        return SummarizedResult(
            url=scraped_content.url,
            summary="No content available to summarize",
            search_query=search_query,
            user_question=user_question,
            key_points=[],
            relevance_score=0,
        )
    
    logger.info(f"Summarizing content from: {scraped_content.url}")
    
    chain = create_summarization_chain()
    
    result = chain.invoke({
        "user_question": user_question,
        "search_query": search_query,
        "web_page_content": scraped_content.content[:settings.result_text_max_characters],
    })
    
    # Ensure URL is set
    result.url = scraped_content.url
    
    logger.info(
        f"Summarized {scraped_content.url}: relevance={result.relevance_score}, "
        f"points={len(result.key_points)}"
    )
    
    return result