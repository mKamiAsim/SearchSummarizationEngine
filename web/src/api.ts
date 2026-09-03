import type { ApiErrorBody, ResearchReport } from "./types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  return (
    typeof value === "object" &&
    value !== null &&
    "message" in value &&
    typeof (value as ApiErrorBody).message === "string"
  );
}

export async function runResearch(query: string): Promise<ResearchReport> {
  const response = await fetch(`${API_BASE_URL}/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new Error(`Request failed (${response.status}).`);
  }

  if (!response.ok) {
    if (isApiErrorBody(payload)) {
      throw new Error(payload.message);
    }
    throw new Error(`Request failed (${response.status}).`);
  }

  return payload as ResearchReport;
}
