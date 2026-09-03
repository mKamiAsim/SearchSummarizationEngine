# Search Summarizer UI

Vite + React + TypeScript chat UI for the Search Summarizer API. Each send is an independent `POST /research` call. Prior Q&A cards stay in this tab for scrolling; they are **not** sent back to the API.

## Prerequisites

The API should already be running on port 8000 (see `api/README.md`):

```powershell
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

## Configure

Copy `.env.example` to `.env` if needed. Default:

```
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Restart `npm run dev` after changing env vars.

## Run

```powershell
cd web
npm install
npm run dev
```

The app is served at **http://localhost:5173**.

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Local Vite server (port 5173) |
| `npm run build` | Production build |
| `npm run preview` | Preview the production build (port 4173) |
