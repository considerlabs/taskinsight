const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// ─── Flow ────────────────────────────────────────────────────────────────────

export interface Stage {
  stage: string;
  issue_count: number;
  avg_days_in_stage: number;
  avg_total_days: number;
  high_risk_count: number;
}

export interface StagesResponse {
  stages: Stage[];
  weekly_throughput: number;
  weekly_throughput_avg: number;
}

export function fetchStages(params: { project_id?: number; period_months?: number } = {}) {
  const q = new URLSearchParams();
  if (params.project_id) q.set("project_id", String(params.project_id));
  if (params.period_months) q.set("period_months", String(params.period_months));
  return request<StagesResponse>(`/v1/flow/stages?${q}`);
}

export interface Issue {
  issue_id: number;
  subject: string;
  flow_stage: string;
  project_id: number;
  project_name: string;
  assigned_to_id: number | null;
  assignee_name: string | null;
  days_in_stage: number;
  total_days: number;
  risk_score: number;
  is_rework: boolean;
  updated_on: string;
  has_explanation: boolean;
}

export interface IssuesResponse {
  issues: Issue[];
  total: number;
  limit: number;
  offset: number;
}

export function fetchIssues(params: {
  project_id?: number;
  flow_stage?: string;
  period_months?: number;
  risk_min?: number;
  sort_by?: string;
  limit?: number;
  offset?: number;
} = {}) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) q.set(k, String(v));
  });
  return request<IssuesResponse>(`/v1/flow/issues?${q}`);
}

export interface ExplanationResponse {
  issue_id: number;
  explanation: string;
  generated_at: string;
  model_version: string;
  cached: boolean;
}

export function fetchExplanation(issueId: number) {
  return request<ExplanationResponse>(`/v1/flow/issue/${issueId}/explanation`);
}

// ─── Dashboard ───────────────────────────────────────────────────────────────

export interface DashboardSummary {
  speed: {
    avg_lead_time_days: number;
    avg_cycle_time_days: number;
    weekly_throughput: number;
    throughput_delta: number;
    forecast_p50_weeks: number | null;
    backlog_count: number;
  };
  effectiveness: {
    total_wip: number;
    unassigned: number;
    gini_index: number;
    top3_wip_ratio: number;
    assignee_counts: { user_id: number; wip: number }[];
  };
  quality: {
    total_issues: number;
    rework_count: number;
    rework_rate: number;
    anomaly_count: number;
    extreme_count: number;
  };
}

export function fetchDashboard(project_id?: number) {
  const q = project_id ? `?project_id=${project_id}` : "";
  return request<DashboardSummary>(`/v1/dashboard/summary${q}`);
}

// ─── Reports ─────────────────────────────────────────────────────────────────

export interface WeeklyReport {
  id?: number;
  period_start: string;
  period_end: string;
  throughput: { current: number; previous: number; delta: number };
  bottleneck: { stage: string; count: number; avg_days: number }[];
  forecast: { p50_weeks: number; p85_weeks: number; p95_weeks: number; change_weeks?: number };
  narrative_text: string;
  generated_at: string;
}

export function fetchLatestReport(project_id?: number) {
  const q = project_id ? `?project_id=${project_id}` : "";
  return request<WeeklyReport>(`/v1/reports/weekly/latest${q}`);
}

export function generateReport(project_id?: number) {
  const q = project_id ? `?project_id=${project_id}` : "";
  return request<WeeklyReport>(`/v1/reports/weekly/generate${q}`, { method: "POST" });
}

// ─── Connectors ──────────────────────────────────────────────────────────────

export interface ConnectorInstance {
  id: number;
  connector_type: string;
  instance_name: string;
  config: { base_url: string; lookback_days: number; [k: string]: unknown };
  is_active: boolean;
  updated_at: string;
}

export interface ConnectorsResponse {
  instances: ConnectorInstance[];
  coming_soon: { connector_type: string; display_name: string }[];
}

export function fetchConnectors() {
  return request<ConnectorsResponse>("/v1/connectors/instances");
}

export function testConnection(connector_type: string, config: Record<string, unknown>) {
  return request<{ ok: boolean; error?: string; user?: string }>("/v1/connectors/test", {
    method: "POST",
    body: JSON.stringify({ connector_type, config }),
  });
}

export function updateConnector(id: number, data: {
  instance_name?: string;
  config?: Record<string, unknown>;
  is_active?: boolean;
}) {
  return request<{ ok: boolean }>(`/v1/connectors/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function syncConnector(id: number) {
  return request<{ ok: boolean; sync: Record<string, unknown>; etl: Record<string, unknown> }>(
    `/v1/connectors/${id}/sync`,
    { method: "POST" }
  );
}
