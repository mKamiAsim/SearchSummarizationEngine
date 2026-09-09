"""
LangGraph research orchestrator — primary CLI and library entrypoint.
"""

from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from langsmith import traceable

from .config.settings import Settings, get_settings
from .core.models import ResearchReport
from .core.observability import configure_langsmith
from .graph.builder import get_compiled_graph
from .graph.state import initial_state
from .utils import get_logger, setup_logging

logger = get_logger("orchestrator")


class ResearchOrchestrator:
    """Runs the LangGraph research pipeline."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings if settings else get_settings()
        configure_langsmith(self.settings)
        self._setup_logging()
        self._graph = get_compiled_graph()
        logger.info("ResearchOrchestrator initialized (LangGraph)")

    def _setup_logging(self) -> None:
        root_logger = logging.getLogger()
        if not root_logger.handlers:
            setup_logging(self.settings)

    @traceable(name="LangGraph Research Pipeline", run_type="chain")
    def run(
        self,
        user_question: str,
        save_to_file: str | None = None,
        generate_pdf: bool | None = None,
    ) -> ResearchReport:
        """Execute the LangGraph research pipeline."""
        if not user_question or not user_question.strip():
            raise ValueError("user_question cannot be empty")

        start_time = time.time()
        pdf_flag = (
            self.settings.generate_pdf if generate_pdf is None else generate_pdf
        )

        state = initial_state(
            user_question.strip(),
            max_retries=self.settings.max_relevance_retries,
            save_to_file=save_to_file,
            generate_pdf=pdf_flag,
        )

        logger.info("=" * 80)
        logger.info("Starting research for: '%s...'", user_question[:100])
        logger.info("=" * 80)

        try:
            final_state = self._graph.invoke(state)
        except Exception as exc:
            logger.error("Pipeline failed: %s", exc, exc_info=True)
            raise RuntimeError(f"Research pipeline failed: {exc}") from exc

        execution_time_ms = int((time.time() - start_time) * 1000)
        markdown = final_state.get("markdown_report") or ""
        sources = list(final_state.get("sources") or [])
        passed = list(final_state.get("passed_summaries") or [])
        report_mode = final_state.get("report_mode") or "full"
        prior = list(final_state.get("prior_search_queries") or [])
        current = list(final_state.get("search_queries") or [])

        report = ResearchReport(
            user_question=user_question.strip(),
            report_content=markdown,
            search_queries_used=prior + current,
            sources=sources,
            summary_count=len(passed),
            generated_at=datetime.now(timezone.utc).isoformat(),
            metadata={
                "engine": "langgraph",
                "report_mode": report_mode,
                "retry_count": final_state.get("retry_count", 0),
                "relevance_evaluation": final_state.get("relevance_evaluation"),
                "persona": (final_state.get("assistant_persona") or {}).get("persona"),
                "execution_time_ms": execution_time_ms,
            },
            report_mode=report_mode,
            markdown_path=str(final_state.get("markdown_path") or ""),
            pdf_path=str(final_state.get("pdf_path") or ""),
        )

        logger.info(
            "Research complete in %.1fs (%s words, %s sources, mode=%s)",
            execution_time_ms / 1000,
            report.get_word_count(),
            report.get_source_count(),
            report_mode,
        )
        return report

    def run_batch(
        self,
        questions: list[str],
        output_dir: str | None = None,
    ) -> list[ResearchReport]:
        """Run the pipeline for multiple questions."""
        if output_dir is None:
            output_dir = self.settings.output_dir

        reports: list[ResearchReport] = []
        for idx, question in enumerate(questions, start=1):
            logger.info("Processing question %s/%s", idx, len(questions))
            safe_filename = "".join(
                c if c.isalnum() or c in " -_" else "_" for c in question[:50]
            )
            safe_filename = safe_filename.replace(" ", "_").lower()
            filepath = Path(output_dir) / f"{safe_filename}.md"
            try:
                reports.append(self.run(question, save_to_file=str(filepath)))
            except Exception as exc:
                logger.error("Failed to process question %s: %s", idx, exc)
        return reports


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Research Summarization Engine (LangGraph)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  research-engine "What are the latest developments in quantum computing?"
  research-engine "Compare product A and B" --output reports/compare.md
  research-engine "Explain transformers" --no-pdf
        """,
    )
    parser.add_argument("question", type=str, help="Research question")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Markdown output path (PDF written alongside when enabled)",
    )
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="Skip PDF generation",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
    )
    args = parser.parse_args()

    settings = get_settings()
    settings.log_level = args.log_level
    setup_logging(settings)

    orchestrator = ResearchOrchestrator(settings=settings)

    output_file = args.output
    if output_file is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_question = "".join(
            c if c.isalnum() or c in " -_" else "_" for c in args.question[:30]
        )
        output_file = f"reports/{timestamp}_{safe_question}.md"

    try:
        report = orchestrator.run(
            args.question,
            save_to_file=output_file,
            generate_pdf=not args.no_pdf,
        )
        print("\n" + "=" * 80)
        print("RESEARCH COMPLETE")
        print("=" * 80)
        print(f"Question: {args.question}")
        print(
            f"Report: {report.get_word_count()} words, "
            f"{report.get_source_count()} sources"
        )
        print(f"Mode: {report.report_mode}")
        print(f"Markdown: {report.markdown_path or output_file}")
        if report.pdf_path:
            print(f"PDF: {report.pdf_path}")
        print("=" * 80)
        return 0
    except Exception as exc:
        logger.error("Research failed: %s", exc)
        print(f"\nError: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
