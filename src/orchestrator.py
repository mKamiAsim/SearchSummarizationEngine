"""
Main orchestrator for the research summarization engine.

This module coordinates all pipeline stages and provides the primary interface
for executing research queries.
"""

import argparse
import logging
import time
from datetime import datetime
from pathlib import Path

from langsmith import traceable

from .chains import (
    select_assistant,
    generate_search_queries,
    summarize_content,
    compile_report,
)
from .config.settings import Settings, get_settings
from .core.models import PipelineState, ResearchReport
from .core.observability import configure_langsmith
from .utils import scrape_urls, setup_logging, get_logger, search_multiple_queries

logger = get_logger("orchestrator")


class ResearchOrchestrator:
    """
    Orchestrates the complete research pipeline.

    This class coordinates all 5 stages of the research engine:
    1. Assistant Selection
    2. Search Query Generation
    3. Web Search Execution
    4. Content Summarization
    5. Report Compilation

    Example:
        >>> orchestrator = ResearchOrchestrator()
        >>> report = orchestrator.run("What are the latest developments in quantum computing?")
        >>> print(report.report_content)
    """

    def __init__(self, settings: Settings | None = None):
        """
        Initialize the research orchestrator.

        Args:
            settings: Custom settings. If None, uses cached global settings.
        """
        self.settings = settings if settings else get_settings()
        configure_langsmith(self.settings)
        self._setup_logging()

        logger.info("ResearchOrchestrator initialized")
        logger.debug(f"Settings: num_queries={self.settings.num_search_queries}, "
                     f"results_per_query={self.settings.num_search_results_per_query}")

    def _setup_logging(self) -> None:
        """Configure logging if not already done."""
        # Check if root logger has handlers
        root_logger = logging.getLogger()
        if not root_logger.handlers:
            setup_logging(self.settings)

    @traceable(name="Research Pipeline", run_type="chain")
    def run(
        self,
        user_question: str,
        save_to_file: str | None = None,
        include_citations: bool | None = None,
        include_search_queries: bool | None = None,
    ) -> ResearchReport:
        """
        Execute the complete research pipeline.

        Args:
            user_question: The research question to investigate
            save_to_file: Optional filepath to save the report (markdown)
            include_citations: Whether to include source URLs (default from settings)
            include_search_queries: Whether to include queries in report (default from settings)

        Returns:
            ResearchReport: Complete research report

        Raises:
            ValueError: If user_question is empty
            RuntimeError: If pipeline fails critically

        Example:
            >>> orchestrator = ResearchOrchestrator()
            >>> report = orchestrator.run("What is quantum entanglement?")
            >>> print(f"Report: {report.get_word_count()} words")
            >>> report.save_to_file("reports/quantum_entanglement.md")
        """
        if not user_question or not user_question.strip():
            raise ValueError("user_question cannot be empty")

        # Initialize pipeline state
        start_time = time.time()
        state = PipelineState(user_question=user_question.strip())

        logger.info("=" * 80)
        logger.info(
            f"Starting research pipeline for: '{user_question[:100]}...'")
        logger.info("=" * 80)

        try:
            # =========================================================================
            # Stage 1: Assistant Selection
            # =========================================================================
            logger.info("\n[Stage 1/5] Selecting assistant persona...")
            persona = select_assistant(state.user_question)
            state.assistant_persona = persona
            logger.info(f"✓ Selected: {persona.persona}")

            # =========================================================================
            # Stage 2: Search Query Generation
            # =========================================================================
            logger.info("\n[Stage 2/5] Generating search queries...")
            query_result = generate_search_queries(
                state.user_question,
                persona,
                num_queries=self.settings.num_search_queries,
            )
            state.search_queries = query_result.queries
            logger.info(
                f"✓ Generated {len(query_result.queries)} queries: {query_result.queries}")

            # =========================================================================
            # Stage 3: Web Search Execution
            # =========================================================================
            logger.info("\n[Stage 3/5] Executing web searches...")
            all_search_results = search_multiple_queries(
                state.search_queries,
                results_per_query=self.settings.num_search_results_per_query,
                delay_between_queries=self.settings.search_delay_seconds,
                settings=self.settings,
            )
            state.search_results = all_search_results
            logger.info(f"✓ Found {len(all_search_results)} unique URLs")

            if not all_search_results:
                logger.warning(
                    "No search results found - proceeding with empty results")

            # =========================================================================
            # Stage 4: Content Summarization
            # =========================================================================
            logger.info("\n[Stage 4/5] Scraping and summarizing content...")

            # Extract URLs from search results
            urls = [result.url for result in all_search_results if result.url]

            if urls:
                # Scrape all URLs
                scraped_contents = scrape_urls(
                    urls,
                    max_characters_per_url=self.settings.result_text_max_characters,
                    settings=self.settings,
                )
                state.scraped_content = scraped_contents

                # Summarize each scraped content
                summaries = []
                for scraped in scraped_contents:
                    # Find the corresponding search query
                    search_query = ""
                    for result in all_search_results:
                        if result.url == scraped.url:
                            search_query = result.search_query
                            break

                    summary = summarize_content(
                        scraped_content=scraped,
                        user_question=state.user_question,
                        search_query=search_query,
                    )
                    summaries.append(summary)

                state.summaries = summaries
                logger.info(f"✓ Summarized {len(summaries)} sources")
            else:
                logger.warning(
                    "No URLs to scrape - proceeding with empty summaries")
                state.summaries = []

            # =========================================================================
            # Stage 5: Report Compilation
            # =========================================================================
            logger.info("\n[Stage 5/5] Compiling research report...")

            # Use settings defaults if not specified
            if include_citations is None:
                include_citations = self.settings.include_citations
            if include_search_queries is None:
                include_search_queries = self.settings.include_search_queries

            report = compile_report(
                user_question=state.user_question,
                summaries=state.summaries,
                persona=persona,
                search_queries=state.search_queries,
                include_citations=include_citations,
                include_search_queries=include_search_queries,
            )
            state.final_report = report
            logger.info(
                f"✓ Report compiled: {report.get_word_count()} words, {report.get_source_count()} sources")

            # =========================================================================
            # Save to file if requested
            # =========================================================================
            if save_to_file:
                self._save_report(report, save_to_file)

            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            state.execution_time_ms = execution_time_ms

            logger.info("\n" + "=" * 80)
            logger.info(
                f"✓ Research pipeline completed in {execution_time_ms / 1000:.1f}s")
            logger.info("=" * 80)

            return report

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            state.add_error(str(e))
            raise RuntimeError(f"Research pipeline failed: {e}") from e

    def _save_report(self, report: ResearchReport, filepath: str) -> None:
        """
        Save report to file.

        Args:
            report: Report to save
            filepath: Destination filepath
        """
        path = Path(filepath)

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Save report
        report.save_to_file(str(path))

        logger.info(f"✓ Report saved to: {path}")

    def run_batch(
        self,
        questions: list[str],
        output_dir: str | None = None,
    ) -> list[ResearchReport]:
        """
        Run research pipeline for multiple questions.

        Args:
            questions: List of research questions
            output_dir: Directory to save reports (default: settings.output_dir)

        Returns:
            list[ResearchReport]: List of generated reports

        Example:
            >>> orchestrator = ResearchOrchestrator()
            >>> questions = ["What is AI?", "What is quantum computing?"]
            >>> reports = orchestrator.run_batch(questions, output_dir="reports")
        """
        if output_dir is None:
            output_dir = self.settings.output_dir

        reports = []

        for idx, question in enumerate(questions, start=1):
            logger.info(f"\n{'='*80}")
            logger.info(f"Processing question {idx}/{len(questions)}")
            logger.info(f"{'='*80}\n")

            # Generate filename from question
            safe_filename = "".join(
                c if c.isalnum() or c in " -_" else "_" for c in question[:50])
            safe_filename = safe_filename.replace(" ", "_").lower()
            filepath = Path(output_dir) / f"{safe_filename}.md"

            try:
                report = self.run(question, save_to_file=str(filepath))
                reports.append(report)
            except Exception as e:
                logger.error(f"Failed to process question {idx}: {e}")
                # Continue with next question

        logger.info(
            f"\nBatch complete: {len(reports)}/{len(questions)} successful")

        return reports


def main():
    """Command-line interface for the research engine."""
    parser = argparse.ArgumentParser(
        description="Research Summarization Engine - Autonomous web research with LLMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a single research query
  python -m src.orchestrator "What are the latest developments in quantum computing?"
  
  # Save report to specific file
  python -m src.orchestrator "Explain transformer architecture" --output reports/transformers.md
  
  # Run with debug logging
  python -m src.orchestrator "What is reinforcement learning?" --log-level DEBUG
        """,
    )

    parser.add_argument(
        "question",
        type=str,
        help="Research question to investigate",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output filepath for the report (default: reports/<timestamp>.md)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Initialize orchestrator
    settings = get_settings()
    settings.log_level = args.log_level
    setup_logging(settings)

    orchestrator = ResearchOrchestrator(settings=settings)

    # Generate output filename if not specified
    output_file = args.output
    if output_file is None:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_question = "".join(
            c if c.isalnum() or c in " -_" else "_" for c in args.question[:30])
        output_file = f"reports/{timestamp}_{safe_question}.md"

    # Run research
    try:
        report = orchestrator.run(args.question, save_to_file=output_file)

        # Print summary
        print("\n" + "=" * 80)
        print("RESEARCH COMPLETE")
        print("=" * 80)
        print(f"Question: {args.question}")
        print(
            f"Report: {report.get_word_count()} words, {report.get_source_count()} sources")
        print(f"Output: {output_file}")
        print("=" * 80)

    except Exception as e:
        logger.error(f"Research failed: {e}")
        print(f"\nError: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
