"""
Stage 5: Report Compilation Chain.

Compiles all summaries into a comprehensive research report.
"""

import logging
from datetime import datetime

from langchain_core.runnables import Runnable

from config.settings import get_settings
from core.llm_factory import create_llm
from core.models import SummarizedResult, ResearchReport, AssistantPersona
from prompts import get_report_compilation_prompt

logger = logging.getLogger(__name__)


def create_report_compilation_chain() -> Runnable:
    """
    Create the report compilation chain using LCEL.

    Returns:
        Runnable: Chain that takes summaries + context and returns markdown report

    Example:
        >>> chain = create_report_compilation_chain()
        >>> result = chain.invoke({
        ...     "user_question": "What is quantum computing?",
        ...     "assistant_persona": "Quantum Computing Researcher",
        ...     "assistant_expertise": "...",
        ...     "assistant_approach": "...",
        ...     "all_summaries": "Source 1: ..."
        ... })
        >>> print(result)
    """
    settings = get_settings()

    # Load prompt template
    prompt = get_report_compilation_prompt()

    # Create LLM
    llm = create_llm(settings=settings)

    # Build chain: prompt -> llm
    # Note: No parser needed - we want raw markdown text
    chain = prompt | llm

    logger.debug("Created report compilation chain")

    return chain


def format_summaries_for_compilation(
    summaries: list[SummarizedResult],
    include_citations: bool = True,
) -> str:
    """
    Format summaries into a single string for the compilation prompt.

    Args:
        summaries: List of summarized results
        include_citations: Whether to include URLs

    Returns:
        str: Formatted summaries string
    """
    formatted_parts = []

    for idx, summary in enumerate(summaries, start=1):
        parts = [
            f"Source {idx}:",
            f"URL: {summary.url}",
            f"Search Query: {summary.search_query}",
            f"Relevance Score: {summary.relevance_score}/100",
            f"Summary: {summary.summary}",
        ]

        if summary.key_points:
            points = "\n".join(f"  - {point}" for point in summary.key_points)
            parts.append(f"Key Points:\n{points}")

        formatted_parts.append("\n".join(parts))

    return "\n\n".join(formatted_parts)


def compile_report(
    user_question: str,
    summaries: list[SummarizedResult],
    persona: AssistantPersona,
    search_queries: list[str] | None = None,
    include_citations: bool = True,
    include_search_queries: bool = True,
) -> ResearchReport:
    """
    Compile all summaries into a comprehensive research report.

    Args:
        user_question: Original research question
        summaries: List of summarized results
        persona: Selected assistant persona
        search_queries: List of search queries used
        include_citations: Whether to include source URLs
        include_search_queries: Whether to include search queries in report

    Returns:
        ResearchReport: Complete research report with metadata

    Example:
        >>> summaries = [SummarizedResult(...), ...]
        >>> persona = AssistantPersona(...)
        >>> report = compile_report("What is quantum computing?", summaries, persona)
        >>> print(report.report_content)
    """
    settings = get_settings()

    logger.info(f"Compiling research report from {len(summaries)} summaries")

    # Format summaries for prompt
    all_summaries_text = format_summaries_for_compilation(
        summaries,
        include_citations=include_citations,
    )

    # Create chain and invoke
    chain = create_report_compilation_chain()

    report_content = chain.invoke({
        "user_question": user_question,
        "assistant_persona": persona.persona,
        "assistant_expertise": persona.expertise,
        "assistant_approach": persona.approach,
        "all_summaries": all_summaries_text,
    })

    # Extract content from AIMessage if needed
    if hasattr(report_content, "content"):
        report_content = report_content.content

    # Add metadata header if requested
    metadata_header = ""
    if include_search_queries and search_queries:
        metadata_header = (
            "## Research Metadata\n\n"
            f"**Search Queries Used:**\n"
            + "\n".join(f"- {q}" for q in search_queries)
            + "\n\n"
        )

    # Combine metadata and report
    final_report = metadata_header + report_content

    # Create ResearchReport model
    sources = [s.url for s in summaries if s.url]

    report = ResearchReport(
        user_question=user_question,
        report_content=final_report,
        search_queries_used=search_queries or [],
        sources=sources,
        summary_count=len(summaries),
        generated_at=datetime.utcnow().isoformat() + "Z",
        metadata={
            "persona": persona.persona,
            "expertise": persona.expertise,
            "settings": {
                "include_citations": include_citations,
                "include_search_queries": include_search_queries,
            },
        },
    )

    logger.info(
        f"Report compiled: {report.get_word_count()} words, "
        f"{report.get_source_count()} sources"
    )

    return report
