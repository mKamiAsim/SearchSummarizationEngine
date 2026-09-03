# Search Summarizer API

Thin FastAPI wrapper around `ResearchOrchestrator`. Each `POST /research` call is an independent pipeline run: no session, memory, or cache across requests.

## Prerequisites

From the repository root, install the existing agent environment, then the API extras:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pip install -r api/requirements.txt
```

Configure `.env` as documented in the project root README (LM Studio / OpenAI-compatible endpoint).

## Run

From the **repository root** (so `src` and `api` are both importable):

```powershell
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

- API: http://127.0.0.1:8000
- OpenAPI docs: http://127.0.0.1:8000/docs

## Endpoints

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| `GET` | `/health` | — | `{"status": "ok"}` |
| `POST` | `/research` | `{"query": "string"}` | Full `ResearchReport` JSON |

Example:

```powershell
curl -X POST http://127.0.0.1:8000/research -H "Content-Type: application/json" -d "{\"query\": \"What is quantum entanglement?\"}"
```

Empty or whitespace-only `query` returns **400**. Orchestrator failures return **500** with a structured JSON body:

```json
{"error": "orchestrator_failure", "message": "...", "status_code": 500}
```

CORS is enabled for the local Vite origins `http://localhost:5173` and `http://127.0.0.1:5173` (plus preview port 4173).
