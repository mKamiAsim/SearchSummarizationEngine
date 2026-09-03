"""
FastAPI app wrapping ResearchOrchestrator.

Run from the repository root:

    uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.models import (
    ErrorResponse,
    HealthResponse,
    ResearchReportResponse,
    ResearchRequest,
)
logger = logging.getLogger("api")

orchestrator = None


def get_orchestrator():
    """Lazy-init a process-wide orchestrator. Each `run()` is still independent."""
    global orchestrator
    if orchestrator is None:
        from src.orchestrator import ResearchOrchestrator

        orchestrator = ResearchOrchestrator()
        logger.info("ResearchOrchestrator ready")
    return orchestrator


app = FastAPI(
    title="Search Summarizer API",
    description="HTTP wrapper around the LangChain research orchestrator.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:4001",
        "http://127.0.0.1:4001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _error_payload(status_code: int, error: str, message: str) -> JSONResponse:
    body = ErrorResponse(error=error, message=message, status_code=status_code)
    return JSONResponse(status_code=status_code, content=body.model_dump())


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post(
    "/research",
    response_model=ResearchReportResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def research(payload: ResearchRequest) -> ResearchReportResponse:
    query = (payload.query or "").strip()
    if not query:
        return _error_payload(
            400,
            "empty_query",
            "Query must be a non-empty string.",
        )

    try:
        engine = get_orchestrator()
        report = await asyncio.to_thread(engine.run, query)
    except ValueError as exc:
        return _error_payload(400, "invalid_query", str(exc))
    except Exception as exc:
        logger.exception("Orchestrator failed")
        return _error_payload(
            500,
            "orchestrator_failure",
            str(exc) or "Research pipeline failed.",
        )

    return ResearchReportResponse(
        user_question=report.user_question,
        report_content=report.report_content,
        search_queries_used=list(report.search_queries_used),
        sources=list(report.sources),
        summary_count=report.summary_count,
        generated_at=report.generated_at,
        metadata=dict(report.metadata) if report.metadata else {},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="http_error",
            message=str(exc.detail),
            status_code=exc.status_code,
        ).model_dump(),
    )
