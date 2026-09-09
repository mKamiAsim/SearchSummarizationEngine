# Search Summarizer API

FastAPI wrapper around the LangGraph `ResearchOrchestrator`.

Prefer the root launcher:

```powershell
python serve.py
# or
python serve.py --api-only
```

## Manual run

From the repository root:

```powershell
python -m pip install -e ".[dev]"
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

- API: http://127.0.0.1:8000
- Docs: http://127.0.0.1:8000/docs

When `web/dist` exists (after `python serve.py --prod`), the same process also
serves the Web UI at `/`.

## Endpoints

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| `GET` | `/health` | — | `{"status": "ok"}` |
| `POST` | `/research` | `{"query": "string"}` | Research report JSON |

Empty queries return **400**. Pipeline failures return **500** with a structured body.
CORS allows local Vite origins (port **4001**) and same-origin production use.
