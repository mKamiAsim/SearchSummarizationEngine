/** Mirrors `ResearchReport` from the orchestrator / POST /research. */
export type ResearchReport = {
  user_question: string;
  report_content: string;
  search_queries_used: string[];
  sources: string[];
  summary_count: number;
  generated_at: string;
  metadata: Record<string, unknown>;
};

export type ApiErrorBody = {
  error: string;
  message: string;
  status_code: number;
};

export type QaCard = {
  id: string;
  query: string;
  status: "loading" | "ready" | "error";
  report?: ResearchReport;
  error?: string;
};
