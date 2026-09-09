"""
FastAPI app wrapping the LangGraph ResearchOrchestrator.

Run from the repository root:

    python serve.py
    # or API only:
    uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api.models import (
    ErrorResponse,
    HealthResponse,
    ResearchReportResponse,
    ResearchRequest,
)

logger = logging.getLogger("api")

orchestrator = None
PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_DIST = PROJECT_ROOT / "web" / "dist"


def get_orchestrator():
    """Lazy-init a process-wide orchestrator. Each `run()` is still independent."""
    global orchestrator
    if orchestrator is None:
        from src.orchestrator import ResearchOrchestrator

        orchestrator = ResearchOrchestrator()
        logger.info("ResearchOrchestrator ready (LangGraph)")
    return orchestrator


app = FastAPI(
    title="Search Summarizer API",
    description="HTTP wrapper around the LangGraph research pipeline.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4001",
        "http://127.0.0.1:4001",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
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
        report_mode=getattr(report, "report_mode", "full"),
        markdown_path=getattr(report, "markdown_path", "") or "",
        pdf_path=getattr(report, "pdf_path", "") or "",
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


def mount_web_ui() -> None:
    """Serve the built Vite SPA from web/dist when present (production mode)."""
    if not WEB_DIST.is_dir():
        logger.info("No web/dist found — API-only mode (use Vite for UI in dev)")
        return

    assets = WEB_DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    index = WEB_DIST / "index.html"
    reserved = {
        "health",
        "research",
        "docs",
        "redoc",
        "openapi.json",
        "assets",
    }

    @app.get("/")
    async def spa_index():
        return FileResponse(index)

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        first = full_path.split("/", 1)[0]
        if first in reserved:
            return JSONResponse(
                status_code=404,
                content={"error": "not_found", "message": f"/{full_path}"},
            )
        candidate = WEB_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)

    logger.info("Serving Web UI from %s", WEB_DIST)


mount_web_ui()
