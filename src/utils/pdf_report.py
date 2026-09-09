"""Professional PDF report writer using reportlab (Windows + Linux compatible)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _inline_md_to_reportlab(text: str) -> str:
    """Convert a subset of Markdown inline markup to ReportLab XML."""
    text = _escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r"<font face='Courier'>\1</font>", text)
    text = re.sub(r"\[(\d+)\]", r"<b>[\1]</b>", text)
    return text


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    styles = {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=28,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1a1a1a"),
            spaceAfter=18,
        ),
        "cover_meta": ParagraphStyle(
            "CoverMeta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#444444"),
            spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "BodyH1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            spaceBefore=16,
            spaceAfter=8,
            textColor=colors.HexColor("#111111"),
        ),
        "h2": ParagraphStyle(
            "BodyH2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.HexColor("#222222"),
        ),
        "body": ParagraphStyle(
            "BodyTextJustified",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            textColor=colors.HexColor("#1f1f1f"),
        ),
        "caution": ParagraphStyle(
            "Caution",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#7a3e00"),
            backColor=colors.HexColor("#fff4e5"),
            borderPadding=8,
            spaceBefore=8,
            spaceAfter=12,
        ),
        "bullet": ParagraphStyle(
            "BulletText",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
            leftIndent=12,
            spaceAfter=3,
        ),
    }
    return styles


def _markdown_to_flowables(markdown_body: str, styles: dict[str, ParagraphStyle]) -> list:
    """Parse simple Markdown structure into Platypus flowables."""
    flowables: list = []
    lines = markdown_body.splitlines()
    i = 0
    bullet_buffer: list[str] = []

    def flush_bullets() -> None:
        nonlocal bullet_buffer
        if not bullet_buffer:
            return
        items = [
            ListItem(Paragraph(_inline_md_to_reportlab(b), styles["bullet"]))
            for b in bullet_buffer
        ]
        flowables.append(ListFlowable(items, bulletType="bullet", leftIndent=18))
        flowables.append(Spacer(1, 6))
        bullet_buffer = []

    # Skip the first H1 (used on cover).
    skipped_title = False
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()
        if not stripped:
            flush_bullets()
            i += 1
            continue

        if stripped.startswith("# ") and not skipped_title:
            skipped_title = True
            i += 1
            continue

        if stripped.startswith("## "):
            flush_bullets()
            heading = stripped[3:].strip()
            style = styles["caution"] if heading.lower() == "caution" else styles["h1"]
            flowables.append(Paragraph(_inline_md_to_reportlab(heading), style))
            i += 1
            continue

        if stripped.startswith("### "):
            flush_bullets()
            flowables.append(
                Paragraph(_inline_md_to_reportlab(stripped[4:].strip()), styles["h2"])
            )
            i += 1
            continue

        if re.match(r"^[-*]\s+", stripped) or re.match(r"^\d+\.\s+", stripped):
            item = re.sub(r"^([-*]|\d+\.)\s+", "", stripped)
            bullet_buffer.append(item)
            i += 1
            continue

        flush_bullets()
        flowables.append(Paragraph(_inline_md_to_reportlab(stripped), styles["body"]))
        i += 1

    flush_bullets()
    return flowables


def write_pdf_report(
    *,
    output_path: str,
    title: str,
    user_question: str,
    markdown_body: str,
    sources: list[str],
    report_mode: str = "full",
) -> str:
    """
    Write a professionally styled PDF report.

    Compatible with Windows and Linux via pure-Python reportlab wheels.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    styles = _build_styles()
    doc = SimpleDocTemplate(
        str(path),
        pagesize=LETTER,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=title,
        author="Search Summarization Engine",
    )

    story: list = []
    generated = datetime.now(timezone.utc).strftime("%d %B %Y")

    story.append(Spacer(1, 1.8 * inch))
    story.append(Paragraph(_escape(title), styles["cover_title"]))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(f"Date: {_escape(generated)}", styles["cover_meta"]))
    story.append(
        Paragraph(
            f"Question: {_escape(user_question[:300])}",
            styles["cover_meta"],
        )
    )
    if report_mode == "insufficient_sources":
        story.append(Spacer(1, 0.4 * inch))
        story.append(
            Paragraph(
                "Caution: Relevant sources were insufficient to produce a "
                "high-confidence report. Findings are limited to available evidence.",
                styles["caution"],
            )
        )
    story.append(PageBreak())

    story.extend(_markdown_to_flowables(markdown_body, styles))

    # Ensure references exist even if the model omitted them.
    if sources and "references" not in markdown_body.lower():
        story.append(Paragraph("References", styles["h1"]))
        for idx, url in enumerate(sources, start=1):
            story.append(
                Paragraph(f"{idx}. {_escape(url)}", styles["body"])
            )

    doc.build(story)
    return str(path)
