import { getToken, removeToken } from "./auth";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    credentials: "include",
    ...init,
  });
  if (res.status === 401) {
    removeToken();
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? `API ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

async function uploadRequest<T>(path: string, formData: FormData): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    credentials: "include",
    body: formData,
  });
  if (res.status === 401) {
    removeToken();
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? `API ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export function login(email: string, password: string) {
  return request<LoginResponse>("/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function logout() {
  return request<{ ok: boolean }>("/v1/auth/logout", { method: "POST" });
}

export function getMe() {
  return request<UserProfile>("/v1/auth/me");
}

// ─── Users ────────────────────────────────────────────────────────────────────

export interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  is_system_admin: boolean;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export function fetchUsers(params: { limit?: number; offset?: number; search?: string } = {}) {
  const q = new URLSearchParams();
  if (params.limit) q.set("limit", String(params.limit));
  if (params.offset) q.set("offset", String(params.offset));
  if (params.search) q.set("search", params.search);
  return request<PaginatedResponse<UserProfile>>(`/v1/users?${q}`);
}

export function createUser(data: { email: string; password: string; display_name: string; is_system_admin?: boolean }) {
  return request<UserProfile>("/v1/users", { method: "POST", body: JSON.stringify(data) });
}

export function adminUpdateUser(userId: string, data: { display_name?: string; is_system_admin?: boolean; is_active?: boolean }) {
  return request<UserProfile>(`/v1/users/${userId}`, { method: "PUT", body: JSON.stringify(data) });
}

export function resetUserPassword(userId: string, newPassword: string) {
  return request<void>(`/v1/users/${userId}/reset-password`, {
    method: "POST",
    body: JSON.stringify({ new_password: newPassword }),
  });
}

export function updateProfile(data: { display_name?: string; current_password?: string; new_password?: string }) {
  return request<UserProfile>("/v1/users/me", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// ─── Projects ─────────────────────────────────────────────────────────────────

export interface Project {
  id: number;
  identifier: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Member {
  user_id: string;
  display_name: string | null;
  email: string | null;
  role: "manager" | "member" | "viewer";
}

export interface WorkflowStatus {
  id: number;
  project_id: number;
  name: string;
  color: string;
  position: number;
  is_closed: boolean;
  is_default: boolean;
  flow_stage: string;
}

export interface Milestone {
  id: number;
  project_id: number;
  name: string;
  description: string | null;
  status: string;
  start_date: string | null;
  due_date: string | null;
  issue_count: number;
  closed_count: number;
}

export function fetchProjects(params: { limit?: number; offset?: number } = {}) {
  const q = new URLSearchParams();
  if (params.limit) q.set("limit", String(params.limit));
  if (params.offset) q.set("offset", String(params.offset));
  return request<PaginatedResponse<Project>>(`/v1/projects?${q}`);
}

export function fetchProject(id: number) {
  return request<Project>(`/v1/projects/${id}`);
}

export function createProject(data: { identifier: string; name: string; description?: string }) {
  return request<Project>("/v1/projects", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function fetchProjectMembers(projectId: number) {
  return request<Member[]>(`/v1/projects/${projectId}/members`);
}

export function fetchProjectStatuses(projectId: number) {
  return request<WorkflowStatus[]>(`/v1/projects/${projectId}/statuses`);
}

export function fetchProjectMilestones(projectId: number) {
  return request<Milestone[]>(`/v1/projects/${projectId}/milestones`);
}

export function createMilestone(
  projectId: number,
  data: { name: string; description?: string; status?: string; start_date?: string; due_date?: string }
) {
  return request<Milestone>(`/v1/projects/${projectId}/milestones`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateMilestone(
  projectId: number,
  milestoneId: number,
  data: { name?: string; description?: string; status?: string; start_date?: string | null; due_date?: string | null }
) {
  return request<Milestone>(`/v1/projects/${projectId}/milestones/${milestoneId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteMilestone(projectId: number, milestoneId: number) {
  return request<void>(`/v1/projects/${projectId}/milestones/${milestoneId}`, { method: "DELETE" });
}

export function updateProject(projectId: number, data: { name?: string; description?: string; is_active?: boolean }) {
  return request<Project>(`/v1/projects/${projectId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function addProjectMember(projectId: number, data: { user_id: string; role: string }) {
  return request<Member>(`/v1/projects/${projectId}/members`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateMemberRole(projectId: number, userId: string, role: string) {
  return request<Member>(`/v1/projects/${projectId}/members/${userId}`, {
    method: "PUT",
    body: JSON.stringify({ role }),
  });
}

export function removeProjectMember(projectId: number, userId: string) {
  return request<void>(`/v1/projects/${projectId}/members/${userId}`, { method: "DELETE" });
}

export function fetchWorkflowTransitions(projectId: number) {
  return request<AllowedTransition[]>(`/v1/projects/${projectId}/workflow/transitions`);
}

export function updateWorkflowTransitions(
  projectId: number,
  transitions: { from_status_id: number | null; to_status_id: number; allowed_roles: string[] }[]
) {
  return request<AllowedTransition[]>(`/v1/projects/${projectId}/workflow/transitions`, {
    method: "PUT",
    body: JSON.stringify({ transitions }),
  });
}

export function updateProjectStatuses(projectId: number, statuses: Partial<WorkflowStatus>[]) {
  return request<WorkflowStatus[]>(`/v1/projects/${projectId}/workflow/statuses`, {
    method: "PUT",
    body: JSON.stringify({ statuses }),
  });
}

// ─── Issues ───────────────────────────────────────────────────────────────────

export interface AllowedTransition {
  id: number;
  project_id: number;
  from_status_id: number | null;
  to_status_id: number;
  to_status_name: string | null;
  to_status_color: string | null;
  allowed_roles: string[];
}

export interface TaskIssue {
  id: number;
  project_id: number;
  project_name: string | null;
  status_id: number;
  status_name: string | null;
  status_color: string | null;
  flow_stage: string | null;
  title: string;
  description: string | null;
  reporter_id: string;
  reporter_name: string | null;
  assignee_id: string | null;
  assignee_name: string | null;
  priority: "low" | "normal" | "high" | "urgent";
  tracker: "task" | "bug" | "feature" | "improvement";
  milestone_id: number | null;
  milestone_name: string | null;
  parent_issue_id: number | null;
  start_date: string | null;
  due_date: string | null;
  estimated_hours: number | null;
  done_ratio: number;
  closed_at: string | null;
  source_type: string;
  external_id: number | null;
  created_at: string;
  updated_at: string;
  allowed_transitions: AllowedTransition[];
}

export interface TimeEntry {
  id: number;
  issue_id: number;
  user_id: string;
  user_name: string | null;
  hours: number;
  activity: string;
  spent_on: string;
  description: string | null;
  created_at: string;
}

export interface Attachment {
  id: string;
  issue_id: number;
  uploader_id: string;
  filename: string;
  content_type: string;
  file_size: number;
  created_at: string;
}

export interface IssueCreatePayload {
  title: string;
  description?: string;
  status_id?: number;
  assignee_id?: string;
  priority?: string;
  tracker?: string;
  milestone_id?: number;
  parent_issue_id?: number;
  start_date?: string;
  due_date?: string;
  estimated_hours?: number;
}

export interface IssueUpdatePayload extends Partial<IssueCreatePayload> {
  done_ratio?: number;
  note?: string;
}

export interface Journal {
  id: number;
  issue_id: number;
  user_id: string;
  user_name: string | null;
  changes: Record<string, { from: string | null; to: string | null }>;
  note: string | null;
  created_at: string;
}

export function fetchIssueList(
  projectId: number,
  params: {
    status_id?: number;
    assignee_id?: string;
    priority?: string;
    tracker?: string;
    milestone_id?: number;
    sort_by?: string;
    order_dir?: string;
    limit?: number;
    offset?: number;
  } = {}
) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) q.set(k, String(v));
  });
  return request<PaginatedResponse<TaskIssue>>(
    `/v1/projects/${projectId}/issues?${q}`
  );
}

export function fetchIssue(projectId: number, issueId: number) {
  return request<TaskIssue>(`/v1/projects/${projectId}/issues/${issueId}`);
}

export function createIssue(projectId: number, data: IssueCreatePayload) {
  return request<TaskIssue>(`/v1/projects/${projectId}/issues`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateIssue(projectId: number, issueId: number, data: IssueUpdatePayload) {
  return request<TaskIssue>(`/v1/projects/${projectId}/issues/${issueId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteIssue(projectId: number, issueId: number) {
  return request<void>(`/v1/projects/${projectId}/issues/${issueId}`, {
    method: "DELETE",
  });
}

export function fetchJournals(projectId: number, issueId: number) {
  return request<Journal[]>(
    `/v1/projects/${projectId}/issues/${issueId}/journals`
  );
}

export function addJournalNote(projectId: number, issueId: number, note: string) {
  return request<Journal>(
    `/v1/projects/${projectId}/issues/${issueId}/journals`,
    { method: "POST", body: JSON.stringify({ note }) }
  );
}

export function transitionIssue(projectId: number, issueId: number, toStatusId: number, note?: string) {
  return request<TaskIssue>(
    `/v1/projects/${projectId}/issues/${issueId}/transition`,
    { method: "POST", body: JSON.stringify({ to_status_id: toStatusId, note }) }
  );
}

export function fetchTimeEntries(projectId: number, issueId: number) {
  return request<TimeEntry[]>(`/v1/projects/${projectId}/issues/${issueId}/time-entries`);
}

export function createTimeEntry(
  projectId: number,
  issueId: number,
  data: { hours: number; activity: string; spent_on: string; description?: string }
) {
  return request<TimeEntry>(
    `/v1/projects/${projectId}/issues/${issueId}/time-entries`,
    { method: "POST", body: JSON.stringify(data) }
  );
}

export function updateTimeEntry(
  entryId: number,
  data: { hours?: number; activity?: string; spent_on?: string; description?: string }
) {
  return request<TimeEntry>(`/v1/time-entries/${entryId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteTimeEntry(entryId: number) {
  return request<void>(`/v1/time-entries/${entryId}`, { method: "DELETE" });
}

export function fetchAttachments(projectId: number, issueId: number) {
  return request<Attachment[]>(`/v1/projects/${projectId}/issues/${issueId}/attachments`);
}

export function uploadAttachment(projectId: number, issueId: number, file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return uploadRequest<Attachment>(
    `/v1/projects/${projectId}/issues/${issueId}/attachments`,
    formData
  );
}

export function deleteAttachment(attachmentId: string) {
  return request<void>(`/v1/attachments/${attachmentId}`, { method: "DELETE" });
}

export async function downloadAttachment(attachmentId: string, filename: string): Promise<void> {
  const token = getToken();
  const res = await fetch(`${BASE}/v1/attachments/${attachmentId}`, {
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    credentials: "include",
  });
  if (!res.ok) throw new Error("다운로드 실패");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── Insights (14종 카드) ──────────────────────────────────────────────────────

export interface InsightCardDetail {
  label: string;
  value: string;
  secondary: string;
  highlight?: boolean;
}

export interface InsightCard {
  id: string;
  title: string;
  category: string;
  target: "both" | "manager" | "decision";
  zone: "alert" | "monitoring" | "disabled";
  data_status: "real" | "approx" | "mock" | "disabled";
  alert: boolean;
  primary_value: string;
  primary_label: string;
  details: InsightCardDetail[];
  note: string | null;
}

export interface InsightCardsResponse {
  cards: InsightCard[];
  alert_count: number;
  generated_at: string;
}

export function fetchInsightCards(params: { project_id?: number; period_months?: number } = {}) {
  const q = new URLSearchParams();
  if (params.project_id) q.set("project_id", String(params.project_id));
  if (params.period_months) q.set("period_months", String(params.period_months));
  return request<InsightCardsResponse>(`/v1/insights/cards?${q}`);
}

export interface InsightDrilldownIssue {
  issue_id: number;
  subject: string;
  flow_stage: string;
  project_name: string;
  assignee_name: string | null;
  days_in_stage: number;
  total_days: number;
  is_rework: boolean;
}

export interface InsightDrilldownResponse {
  card_id: string;
  issues: InsightDrilldownIssue[];
  total: number;
  limit: number;
  offset: number;
  note?: string;
}

export function fetchInsightCardIssues(
  cardId: string,
  params: { project_id?: number; limit?: number; offset?: number } = {},
) {
  const q = new URLSearchParams();
  if (params.project_id) q.set("project_id", String(params.project_id));
  if (params.limit) q.set("limit", String(params.limit));
  if (params.offset) q.set("offset", String(params.offset));
  return request<InsightDrilldownResponse>(`/v1/insights/cards/${cardId}/issues?${q}`);
}

// ─── Flow (기존 유지) ──────────────────────────────────────────────────────────
// backward-compat aliases for existing flow/page.tsx

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

export interface FlowIssue {
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

export interface FlowIssuesResponse {
  issues: FlowIssue[];
  total: number;
  limit: number;
  offset: number;
}

export type Issue = FlowIssue;
export type IssuesResponse = FlowIssuesResponse;

export function fetchFlowIssues(params: {
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
  return request<FlowIssuesResponse>(`/v1/flow/issues?${q}`);
}

export interface ExplanationResponse {
  issue_id: number;
  explanation: string;
  generated_at: string;
  model_version: string;
  cached: boolean;
}

export const fetchIssues = fetchFlowIssues;

export function fetchExplanation(issueId: number) {
  return request<ExplanationResponse>(`/v1/flow/issue/${issueId}/explanation`);
}

// ─── Dashboard (기존 유지) ─────────────────────────────────────────────────────

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

// ─── Reports (기존 유지) ───────────────────────────────────────────────────────

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

// ─── Connectors (기존 유지) ────────────────────────────────────────────────────

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
