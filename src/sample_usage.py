"""
Sample usage examples for the Research Summarization Engine.

This file demonstrates various ways to use the research engine.
"""

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.orchestrator import ResearchOrchestrator
from src.config.settings import Settings, get_settings


def example_basic_usage():
    """
    Basic usage: Run a single research query.

    This is the simplest way to use the research engine.
    """
    print("=" * 80)
    print("Example 1: Basic Usage")
    print("=" * 80)

    # Initialize orchestrator with default settings
    orchestrator = ResearchOrchestrator()

    # Run a research query
    question = "What are the latest developments in quantum computing?"

    print(f"\nResearching: {question}\n")

    report = orchestrator.run(
        question,
        save_to_file="reports/quantum_computing_example.md",
    )

    # Print report metadata
    print(f"\n✓ Report generated:")
    print(f"  - Words: {report.get_word_count()}")
    print(f"  - Sources: {report.get_source_count()}")
    print(f"  - Summaries: {report.summary_count}")
    print(f"  - Saved to: reports/quantum_computing_example.md")

    # Print first 500 characters of report
    print(f"\n📄 Report Preview (first 500 chars):")
    print("-" * 80)
    print(report.report_content[:500] + "...")
    print("-" * 80)


def example_custom_settings():
    """
    Example with custom settings.

    Demonstrates how to configure the engine with custom parameters.
    """
    print("\n" + "=" * 80)
    print("Example 2: Custom Settings")
    print("=" * 80)

    # Create custom settings
    settings = Settings(
        num_search_queries=3,  # Generate 3 search queries
        num_search_results_per_query=5,  # Get 5 results per query
        result_text_max_characters=15000,  # Extract up to 15k chars per page
        openai_temperature=0.5,  # Slightly more creative responses
        log_level="DEBUG",  # Verbose logging
        include_citations=True,
        include_search_queries=True,
    )

    # Initialize orchestrator with custom settings
    orchestrator = ResearchOrchestrator(settings=settings)

    question = "Explain the impact of transformer architectures on NLP"

    print(f"\nResearching with custom settings: {question}\n")

    report = orchestrator.run(
        question,
        save_to_file="reports/transformers_custom.md",
    )

    print(f"\n✓ Report generated with custom settings:")
    print(f"  - Search queries used: {len(report.search_queries_used)}")
    print(f"  - Sources cited: {len(report.sources)}")


def example_batch_processing():
    """
    Example: Process multiple questions in batch.

    Useful for generating multiple reports automatically.
    """
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

    reports = orchestrator.run_batch(
        questions,
        output_dir="reports/batch",
    )

    print(f"\n✓ Batch complete: {len(reports)} reports generated")

    for idx, report in enumerate(reports, start=1):
        print(
            f"  {idx}. {report.user_question[:60]}... ({report.get_word_count()} words)")


def example_programmatic_access():
    """
    Example: Access report data programmatically.

    Shows how to work with the report object after generation.
    """
    print("\n" + "=" * 80)
    print("Example 4: Programmatic Access")
    print("=" * 80)

    orchestrator = ResearchOrchestrator()

    question = "What is the role of GPUs in deep learning?"

    print(f"\nResearching: {question}\n")

    report = orchestrator.run(question)

    # Access report components
    print("\n📊 Report Metadata:")
    print(f"  Question: {report.user_question}")
    print(f"  Generated: {report.generated_at}")
    print(f"  Word count: {report.get_word_count()}")
    print(f"  Source count: {report.get_source_count()}")
    print(f"  Summaries: {report.summary_count}")

    print("\n🔍 Search Queries Used:")
    for idx, query in enumerate(report.search_queries_used, start=1):
        print(f"  {idx}. {query}")

    print("\n📚 Sources:")
    for idx, source in enumerate(report.sources, start=1):
        print(f"  {idx}. {source}")

    print("\n⚙️ Metadata:")
    for key, value in report.metadata.items():
        print(f"  {key}: {value}")

    # Save in different formats
    report.save_to_file("reports/gpu_deep_learning.md")
    print("\n✓ Report saved to: reports/gpu_deep_learning.md")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("RESEARCH SUMMARIZATION ENGINE - EXAMPLES")
    print("=" * 80)
    print("\n⚠️  Note: These examples will execute real web searches and LLM calls.")
    print("Make sure LM Studio is running and you have internet connection.\n")

    # Uncomment the examples you want to run:

    example_basic_usage()
    # example_custom_settings()
    # example_batch_processing()
    # example_programmatic_access()

    print("\n" + "=" * 80)
    print("To run an example, uncomment it in the main() function")
    print("=" * 80)


if __name__ == "__main__":
    main()
