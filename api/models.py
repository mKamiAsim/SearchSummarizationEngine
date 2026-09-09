"""Pydantic request/response schemas for the research API."""

from typing import Any

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    """Incoming research query."""

    query: str = Field(..., description="User research question")


class ErrorResponse(BaseModel):
    """Structured JSON error payload."""

    error: str = Field(..., description="Short error code or category")
    message: str = Field(..., description="Human-readable error message")
    status_code: int = Field(..., description="HTTP status code")


class HealthResponse(BaseModel):
    """Liveness payload for GET /health."""

    status: str = Field(..., description="Service health status")


class ResearchReportResponse(BaseModel):
    """JSON shape of `src.core.models.ResearchReport`."""

    user_question: str = Field(..., description="Original research question")
    report_content: str = Field(..., description="Full report in markdown")
    search_queries_used: list[str] = Field(
        default_factory=list,
        description="Search queries executed (metadata; not shown in report body)",
    )
    sources: list[str] = Field(
        default_factory=list,
        description="Source URLs",
    )
    summary_count: int = Field(
        default=0,
        description="Number of relevance-passed summaries used",
    )
    generated_at: str = Field(
        default="",
        description="Generation timestamp (ISO)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )
    report_mode: str = Field(
        default="full",
        description="full or insufficient_sources",
    )
    markdown_path: str = Field(default="", description="Saved Markdown path")
    pdf_path: str = Field(default="", description="Saved PDF path")
