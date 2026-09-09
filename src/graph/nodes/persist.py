"""Persist Markdown and PDF report outputs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ...config.settings import get_settings
from ...utils.pdf_report import write_pdf_report
from ..state import ResearchGraphState

logger = logging.getLogger(__name__)


def _default_stem(user_question: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe = "".join(
        c if c.isalnum() or c in " -_" else "_" for c in user_question[:40]
    ).strip().replace(" ", "_").lower()
    return f"{timestamp}_{safe or 'report'}"


def persist_outputs_node(state: ResearchGraphState) -> dict[str, Any]:
    """Write Markdown (and optional PDF) files to disk."""
    settings = get_settings()
    markdown = state.get("markdown_report") or ""
    user_question = state["user_question"]
    sources = list(state.get("sources") or [])
    report_mode = state.get("report_mode") or "full"
    generate_pdf = bool(
        state.get("generate_pdf")
        if state.get("generate_pdf") is not None
        else settings.generate_pdf
    )

    save_to = state.get("save_to_file")
    if save_to:
        md_path = Path(save_to)
        if md_path.suffix.lower() != ".md":
            md_path = md_path.with_suffix(".md")
    else:
        out_dir = Path(settings.output_dir)
        md_path = out_dir / f"{_default_stem(user_question)}.md"

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown, encoding="utf-8")
    logger.info("Markdown report saved: %s", md_path)

    pdf_path_str = ""
    if generate_pdf:
        pdf_path = md_path.with_suffix(".pdf")
        try:
            write_pdf_report(
                output_path=str(pdf_path),
                title=_extract_title(markdown, user_question),
                user_question=user_question,
                markdown_body=markdown,
                sources=sources,
                report_mode=report_mode,
            )
            pdf_path_str = str(pdf_path)
            logger.info("PDF report saved: %s", pdf_path)
        except Exception as exc:
            logger.error("PDF generation failed: %s", exc)

    return {
        "markdown_path": str(md_path),
        "pdf_path": pdf_path_str or None,
    }


def _extract_title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or fallback
    return fallback[:120]
