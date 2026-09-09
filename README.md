# Search Summarization Engine

LangGraph research pipeline that turns a natural-language question into
relevance-gated web research and dual cited reports (**Markdown + PDF**).

Configured by default for a local **LM Studio** OpenAI-compatible endpoint.
Any compatible chat API works via environment variables.

## Architecture

```text
User question
    |
    v
LangGraph StateGraph
    |-- select_assistant
    |-- generate_search_queries  <-----------------------------+
    |-- execute_web_search                                      |
    |       | empty/low quality & retries left -----------------+
    |-- scrape_and_summarize
    |-- assess_relevance  (HF embeddings + LLM 1-5 scoring)
    |       | relevance < 50% & retries left -------------------+
    |-- generate_reports  (full OR insufficient-sources caution)
    `-- persist_outputs   -> reports/*.md + reports/*.pdf
```

Prompts live in `src/graph/prompts.py`. Relevance uses local Hugging Face
sentence embeddings (`sentence-transformers/all-MiniLM-L6-v2`) plus LLM
component-aware scoring. Chat completions use `langchain-openai` as the
OpenAI-compatible adapter for LangGraph (not a separate LCEL chain stack).

## Installation

Requires **Python 3.10+** and **Node.js 18+** (for the Web UI).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Configuration

Create a `.env` in the project root:

```dotenv
OPENAI_API_KEY=lm-studio
OPENAI_API_BASE=http://localhost:1234/v1
OPENAI_MODEL_NAME=qwen/qwen3.5-4b
OPENAI_TEMPERATURE=0.3
OPENAI_MAX_TOKENS=12288

MAX_RELEVANCE_RETRIES=3
GENERATE_PDF=true

# Local Hugging Face embeddings for relevance scoring (not the chat LLM)
EMBEDDING_BACKEND=sentence_transformers
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2

# Web search: Tavily is required for reliable results.
# Get a key at https://app.tavily.com
TAVILY_API_KEY=tvly-your-key
SEARCH_BACKEND=tavily
```

## Host Web API + Web UI

### One command (recommended)

From the repository root:

```powershell
python serve.py
```

This starts:

| Service | URL |
| --- | --- |
| Web UI (Vite) | http://127.0.0.1:4001 |
| Web API | http://127.0.0.1:8000 |
| OpenAPI docs | http://127.0.0.1:8000/docs |

Press **Ctrl+C** to stop both processes.

Other modes:

```powershell
# API only
python serve.py --api-only

# Web UI only (expects API already running)
python serve.py --ui-only

# Production: build UI and serve API + SPA from one process
python serve.py --prod
```

Production URL after `python serve.py --prod`:

- App + API: http://127.0.0.1:8000
- Docs: http://127.0.0.1:8000/docs

Equivalent package entrypoint:

```powershell
research-serve
```

### Manual (two terminals)

API:

```powershell
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Web UI:

```powershell
cd web
npm install
# web/.env → VITE_API_BASE_URL=http://127.0.0.1:8000
npm run dev
```

### API endpoints

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| `GET` | `/health` | — | `{"status": "ok"}` |
| `POST` | `/research` | `{"query": "string"}` | Research report JSON |

```powershell
curl -X POST http://127.0.0.1:8000/research `
  -H "Content-Type: application/json" `
  -d "{\"query\": \"What is quantum entanglement?\"}"
```

Each `POST /research` call is an independent LangGraph run (no chat memory).

## CLI usage

```powershell
research-engine "What are the latest developments in quantum computing?"
research-engine "Compare A and B" --output reports/compare.md --no-pdf
```

Python:

```python
from src.orchestrator import ResearchOrchestrator

report = ResearchOrchestrator().run(
    "What are the latest developments in quantum computing?",
    save_to_file="reports/quantum_computing.md",
)
print(report.report_content)
print(report.pdf_path)
```

## LangSmith Observability

Tracing is optional. To enable:

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-langsmith-api-key
LANGSMITH_PROJECT=search-summarization-engine
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

The legacy `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`, and
`LANGCHAIN_ENDPOINT` names are also supported.

## Testing

```powershell
python -m pytest -o addopts="" tests
ruff check src tests api serve.py
```

## Project layout

```text
serve.py                      Start API + Web UI together
api/                          FastAPI service (+ optional SPA mount)
web/                          Vite + React interactive UI
src/
  orchestrator.py             LangGraph CLI / library entry
  graph/                      StateGraph, nodes, prompts, scoring, routing
  config/settings.py          Environment-backed settings
  core/                       Models, LLM factory, observability
  utils/                      Search, scrape, PDF, parsers, logging
tests/
reports/
```

## Error handling and security

Pipeline failures raise `RuntimeError` with the original cause retained.
External web content is untrusted input. Keep credentials in `.env` only —
never in prompts, logs, or generated reports.
