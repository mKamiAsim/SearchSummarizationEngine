"""PDF report generation smoke tests."""

from pathlib import Path

from src.utils.pdf_report import write_pdf_report


def test_write_pdf_report_full(tmp_path: Path):
    output = tmp_path / "sample.pdf"
    markdown = """# Sample Research Report

## Executive Summary

This is a short executive summary with a citation [1].

## Background

Background context for the topic.

## Detailed Analysis

### Theme One

Analysis details here.

## Key Findings

- Finding one
- Finding two

## Recommendations

Proceed with caution.

## References

1. https://example.com/source
"""
    path = write_pdf_report(
        output_path=str(output),
        title="Sample Research Report",
        user_question="What is the sample topic?",
        markdown_body=markdown,
        sources=["https://example.com/source"],
        report_mode="full",
    )
    assert Path(path).exists()
    assert Path(path).stat().st_size > 500


def test_write_pdf_report_insufficient(tmp_path: Path):
    output = tmp_path / "caution.pdf"
    markdown = """# Limited Findings

## Caution

Relevant sources were insufficient to produce a high-confidence report.

## Limited Findings

No reliable comparative evidence was found.
"""
    path = write_pdf_report(
        output_path=str(output),
        title="Limited Findings",
        user_question="Compare A and B for network use",
        markdown_body=markdown,
        sources=[],
        report_mode="insufficient_sources",
    )
    assert Path(path).exists()
    assert Path(path).stat().st_size > 400
