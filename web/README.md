# Search Summarizer UI

Vite + React + TypeScript UI for the LangGraph research API.

Each send is an independent `POST /research` call. Prior Q&A cards stay visible
in the tab for scrolling; they are **not** sent back to the API.

## Recommended: start with API

From the repository root:

```powershell
python serve.py
```

- Web UI: http://127.0.0.1:4001
- API: http://127.0.0.1:8000

## Manual run

```powershell
cd web
npm install
```

Create `.env` (or let `serve.py` write it):

```
VITE_API_BASE_URL=http://127.0.0.1:8000
```

```powershell
npm run dev
```

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Local Vite server (port **4001**) |
| `npm run build` | Production build into `web/dist` |
| `npm run preview` | Preview the production build |
