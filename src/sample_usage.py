"""
Sample usage examples for the Research Summarization Engine.
"""

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.settings import Settings
from src.orchestrator import ResearchOrchestrator


def example_basic_usage():
    print("=" * 80)
    print("Example 1: Basic Usage (LangGraph)")
    print("=" * 80)

    orchestrator = ResearchOrchestrator()
    question = "What are the latest developments in quantum computing?"
    print(f"\nResearching: {question}\n")

    report = orchestrator.run(
        question,
        save_to_file="reports/quantum_computing_example.md",
    )

    print(f"\n✓ Report generated:")
    print(f"  - Words: {report.get_word_count()}")
    print(f"  - Sources: {report.get_source_count()}")
    print(f"  - Mode: {report.report_mode}")
    print(f"  - Markdown: {report.markdown_path}")
    if report.pdf_path:
        print(f"  - PDF: {report.pdf_path}")


def example_custom_settings():
    print("\n" + "=" * 80)
    print("Example 2: Custom Settings")
    print("=" * 80)

    settings = Settings(
        num_search_queries=3,
        num_search_results_per_query=5,
        result_text_max_characters=15000,
        openai_temperature=0.5,
        log_level="DEBUG",
        include_citations=True,
    )
    orchestrator = ResearchOrchestrator(settings=settings)
    question = "Explain the impact of transformer architectures on NLP"
    print(f"\nResearching with custom settings: {question}\n")

    report = orchestrator.run(
        question,
        save_to_file="reports/transformers_custom.md",
    )
    print(f"\n✓ Report generated with custom settings:")
    print(f"  - Sources cited: {len(report.sources)}")


def example_batch_processing():
    print("\n" + "=" * 80)
    print("Example 3: Batch Processing")
    print("=" * 80)

    orchestrator = ResearchOrchestrator()
    questions = [
        "What is reinforcement learning and how does it work?",
        "Explain the concept of attention mechanisms in transformers",
        "What are the key differences between DQN and policy gradient methods?",
    ]
    print(f"\nProcessing {len(questions)} research questions...\n")
    reports = orchestrator.run_batch(questions, output_dir="reports/batch")
    print(f"\n✓ Batch complete: {len(reports)} reports generated")
    for idx, report in enumerate(reports, start=1):
        print(
            f"  {idx}. {report.user_question[:60]}... ({report.get_word_count()} words)"
        )


if __name__ == "__main__":
    print("Run individual example_* functions after configuring .env and LM Studio.")
