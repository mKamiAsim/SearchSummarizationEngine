import { FormEvent, useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getApiBaseUrl, runResearch } from "./api";
import type { QaCard, ResearchReport } from "./types";

function sourceTitle(url: string): string {
  try {
    const parsed = new URL(url);
    const path = parsed.pathname.replace(/\/$/, "");
    if (path && path !== "/") {
      const last = path.split("/").filter(Boolean).pop() ?? parsed.hostname;
      return `${parsed.hostname} — ${decodeURIComponent(last).replace(/[-_]/g, " ")}`;
    }
    return parsed.hostname;
  } catch {
    return url;
  }
}

function formatTimestamp(iso: string): string {
  if (!iso) {
    return "";
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString();
}

function metadataEntries(metadata: Record<string, unknown>): [string, string][] {
  return Object.entries(metadata).map(([key, value]) => [
    key,
    typeof value === "string" ? value : JSON.stringify(value),
  ]);
}

function QaCardView({ card }: { card: QaCard }) {
  return (
    <article className="qa-card" aria-live={card.status === "loading" ? "polite" : undefined}>
      <p className="card-label">Independent query — prior turns are not sent to the API</p>
      <div className="bubble user-bubble">
        <span className="bubble-role">You</span>
        <p>{card.query}</p>
      </div>

      {card.status === "loading" && (
        <div className="bubble assistant-bubble loading-bubble">
          <span className="bubble-role">Research report</span>
          <div className="spinner-row">
            <span className="spinner" aria-hidden="true" />
            <span>Searching and summarizing… this may take a minute.</span>
          </div>
          <div className="skeleton">
            <div className="skeleton-line wide" />
            <div className="skeleton-line" />
            <div className="skeleton-line medium" />
          </div>
        </div>
      )}

      {card.status === "error" && (
        <div className="bubble error-bubble" role="alert">
          <span className="bubble-role">Request failed</span>
          <p>{card.error ?? "Something went wrong."}</p>
        </div>
      )}

      {card.status === "ready" && card.report && <ReportView report={card.report} />}
    </article>
  );
}

function ReportView({ report }: { report: ResearchReport }) {
  const generated = formatTimestamp(report.generated_at);
  const meta = metadataEntries(report.metadata);

  return (
    <div className="bubble assistant-bubble">
      <span className="bubble-role">Research report</span>
      <div className="meta-row">
        {generated && <span>Generated {generated}</span>}
        <span>
          {report.summary_count} {report.summary_count === 1 ? "summary" : "summaries"}
        </span>
      </div>

      <div className="markdown">
        <Markdown remarkPlugins={[remarkGfm]}>{report.report_content}</Markdown>
      </div>

      <section className="sources">
        <h2>Sources</h2>
        {report.sources.length === 0 ? (
          <p className="muted">No sources returned.</p>
        ) : (
          <ol>
            {report.sources.map((url) => (
              <li key={url}>
                <span className="source-title">{sourceTitle(url)}</span>
                <a href={url} target="_blank" rel="noreferrer">
                  {url}
                </a>
              </li>
            ))}
          </ol>
        )}
      </section>

      {report.search_queries_used.length > 0 && (
        <section className="extra-meta">
          <h3>Search queries used</h3>
          <ul>
            {report.search_queries_used.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ul>
        </section>
      )}

      {meta.length > 0 && (
        <section className="extra-meta">
          <h3>Metadata</h3>
          <dl>
            {meta.map(([key, value]) => (
              <div key={key} className="meta-item">
                <dt>{key}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}
    </div>
  );
}

export default function App() {
  const [query, setQuery] = useState("");
  const [cards, setCards] = useState<QaCard[]>([]);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current?.lastElementChild?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [cards]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) {
      return;
    }

    const id = crypto.randomUUID();
    setCards((prev) => [...prev, { id, query: trimmed, status: "loading" }]);
    setQuery("");

    try {
      const report = await runResearch(trimmed);
      setCards((prev) =>
        prev.map((card) =>
          card.id === id ? { ...card, status: "ready", report } : card,
        ),
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "Request failed.";
      setCards((prev) =>
        prev.map((card) =>
          card.id === id ? { ...card, status: "error", error: message } : card,
        ),
      );
    }
  }

  const submitting = cards.some((card) => card.status === "loading");

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Search Summarizer</h1>
          <p className="subtitle">
            Each question is a fresh research run. History stays in this browser tab only.
          </p>
        </div>
        <p className="api-hint">API {getApiBaseUrl()}</p>
      </header>

      <div className="thread" ref={listRef}>
        {cards.length === 0 && (
          <div className="empty-state">
            <p>Ask a research question to generate a sourced markdown report.</p>
          </div>
        )}
        {cards.map((card) => (
          <QaCardView key={card.id} card={card} />
        ))}
      </div>

      <form className="composer" onSubmit={handleSubmit}>
        <label className="sr-only" htmlFor="query">
          Research question
        </label>
        <textarea
          id="query"
          rows={2}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Ask a research question…"
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
        />
        <button type="submit" disabled={submitting || !query.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
