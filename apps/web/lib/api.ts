const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const DEV_USER = "admin@pamtengo.demo";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-User-Email": DEV_USER,
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* keep status text */
    }
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  overview: () => req<Overview>("/api/v1/analytics/overview"),
  leads: (params: Record<string, string> = {}) => {
    const q = new URLSearchParams(params).toString();
    return req<Paged<LeadItem>>(`/api/v1/leads${q ? `?${q}` : ""}`);
  },
  leadDetail: (id: string) => req<LeadDetail>(`/api/v1/leads/${id}`),
  createLead: (payload: Record<string, unknown>) =>
    req<LeadItem>("/api/v1/leads", { method: "POST", body: JSON.stringify(payload) }),
  updateLead: (id: string, payload: Record<string, unknown>) =>
    req<LeadItem>(`/api/v1/leads/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  qualify: (id: string) => req<AgentRun>(`/api/v1/leads/${id}/qualify`, { method: "POST" }),
  draftOutreach: (id: string) => req<{ run: AgentRun }>(`/api/v1/leads/${id}/draft-outreach`, { method: "POST" }),
  importCsv: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_URL}/api/v1/leads/import`, {
      method: "POST",
      headers: { "X-User-Email": DEV_USER },
      body: form,
    });
    if (!res.ok) throw new ApiError(res.status, await res.text());
    return (await res.json()) as { created: number; skipped_duplicates: number; errors: string[] };
  },
  runs: (params: Record<string, string> = {}) => {
    const q = new URLSearchParams(params).toString();
    return req<Paged<AgentRun>>(`/api/v1/agent-runs${q ? `?${q}` : ""}`);
  },
  runSteps: (id: string) => req<AgentStep[]>(`/api/v1/agent-runs/${id}/steps`),
  run: (id: string) => req<AgentRun>(`/api/v1/agent-runs/${id}`),
  activities: (leadId: string) => req<Activity[]>(`/api/v1/leads/${leadId}/activities`),
  drafts: (params: Record<string, string> = {}) => {
    const q = new URLSearchParams(params).toString();
    return req<Paged<Draft>>(`/api/v1/outreach-drafts${q ? `?${q}` : ""}`);
  },
  editDraft: (id: string, payload: Record<string, unknown>) =>
    req<Draft>(`/api/v1/outreach-drafts/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  approveDraft: (id: string) => req<Draft>(`/api/v1/outreach-drafts/${id}/approve`, { method: "POST" }),
  rejectDraft: (id: string) => req<Draft>(`/api/v1/outreach-drafts/${id}/reject`, { method: "POST" }),
  sendDraft: (id: string, confirm: boolean, key?: string) =>
    req<{ status: string; draft?: Draft }>(`/api/v1/outreach-drafts/${id}/simulate-send`, {
      method: "POST",
      body: JSON.stringify({ confirm, idempotency_key: key }),
    }),
  icp: () => req<Icp[]>("/api/v1/icp"),
  saveIcp: (payload: Record<string, unknown>) =>
    req<Icp>("/api/v1/icp", { method: "POST", body: JSON.stringify(payload) }),
  aiStatus: () => req<AiStatus>("/api/v1/ai/status"),
};

export interface Paged<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
export interface LeadItem {
  id: string;
  company_id: string;
  full_name: string;
  job_title: string | null;
  email: string;
  status: string;
  source: string | null;
  fit_score: number | null;
  fit_explanation: string | null;
  company_name: string | null;
  company_country: string | null;
  company_industry: string | null;
  created_at: string;
  updated_at: string;
}
export interface LeadDetail {
  lead: LeadItem;
  company: Record<string, unknown> | null;
  drafts: Draft[];
  agent_runs: AgentRun[];
}
export interface AgentRun {
  id: string;
  lead_id: string;
  workflow_type: string;
  status: string;
  input_snapshot: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}
export interface AgentStep {
  id: string;
  agent_run_id: string;
  step_name: string;
  status: string;
  input_summary: string | null;
  output_summary: string | null;
  duration_ms: number | null;
  created_at: string;
}
export interface Draft {
  id: string;
  lead_id: string;
  agent_run_id: string | null;
  subject: string;
  body: string;
  evidence: string[];
  status: string;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}
export interface Activity {
  id: string;
  lead_id: string;
  activity_type: string;
  description: string;
  created_at: string;
}
export interface Overview {
  total_leads: number;
  qualified_leads: number;
  drafts_awaiting_approval: number;
  emails_mock_sent: number;
  leads_by_status: { status: string; count: number }[];
  leads_by_country: { country: string; count: number }[];
  recent_runs: AgentRun[];
  how_calculated: string;
}
export interface Icp {
  id: string;
  name: string;
  target_industries: string[];
  target_countries: string[];
  company_size_preferences: string[];
  created_at: string | null;
}
export interface AiStatus {
  configured_provider: string;
  active_provider: string;
  mock_mode: boolean;
  timeout_seconds: number;
  max_retries: number;
  token_budget: number;
}

/** CSV formula-injection guard mirrored from the backend for client-side previews. */
export function sanitizeCsvCell(value: string): string {
  if (value && ["=", "+", "-", "@", "\t", "\r"].includes(value[0])) return `'${value}`;
  return value;
}

export function scoreColor(score: number | null): string {
  if (score === null || score === undefined) return "bg-slate-200 text-slate-600";
  if (score >= 60) return "bg-green-100 text-green-800";
  if (score >= 35) return "bg-amber-100 text-amber-800";
  return "bg-red-100 text-red-800";
}
