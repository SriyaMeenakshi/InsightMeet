import type { Analysis, AskResponse, MeetingSummary, ModelMetrics, SearchHit } from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function describeDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (typeof d?.msg === "string" ? String(d.msg).replace(/^Value error, /, "") : JSON.stringify(d)))
      .join(" ");
  }
  return "Something went wrong.";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError(
      `Cannot reach the InsightMeet backend at ${API_URL}. Start it with "uvicorn app.main:app --port 8000" in the backend folder.`,
      0,
    );
  }
  if (!res.ok) {
    let message = `Request failed (${res.status}).`;
    try {
      const body = await res.json();
      message = describeDetail(body.detail);
    } catch {
      /* keep default */
    }
    throw new ApiError(message, res.status);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  health: () => request<{ status: string; spacy_model: boolean }>("/api/health"),
  analyze: (p: { transcript: string; title?: string; meeting_date?: string }) =>
    request<Analysis>("/api/analyze", json({ ...p, title: p.title || null, meeting_date: p.meeting_date || null })),
  extractText: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<{ filename: string; text: string; characters: number }>("/api/extract-text", {
      method: "POST",
      body: fd,
    });
  },
  example: () => request<{ title: string; meeting_date: string; transcript: string }>("/api/example-transcript"),
  meetings: (q?: string) =>
    request<{ total: number; meetings: MeetingSummary[] }>(`/api/meetings${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  meeting: (id: string) => request<Analysis>(`/api/meetings/${id}`),
  deleteMeeting: (id: string) => request<void>(`/api/meetings/${id}`, { method: "DELETE" }),
  ask: (id: string, question: string) => request<AskResponse>(`/api/meetings/${id}/ask`, json({ question })),
  search: (id: string, q: string) =>
    request<{ query: string; hits: SearchHit[] }>(`/api/meetings/${id}/search?q=${encodeURIComponent(q)}`),
  metrics: () => request<ModelMetrics>("/api/model/metrics"),
};
