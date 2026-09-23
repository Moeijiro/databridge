import type { Credential, Dashboard, FailedRecord, Integration, IntegrationInput, MappingRule, Meta, RunDetail, RunSummary, TestResult, User } from "./types";

export const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      credentials: "include",
      cache: "no-store",
      headers: init.body ? { "Content-Type": "application/json" } : undefined,
      ...init,
    });
  } catch {
    throw new ApiError(0, "network_error", "Can't reach the DataBridge API.");
  }
  if (response.status === 204) return undefined as T;
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const error = (payload as { error?: { code?: string; message?: string; fields?: { field: string; message: string }[] } } | null)?.error;
    const fields = error?.fields?.map((f) => `${f.field}: ${f.message}`).join(" · ");
    throw new ApiError(response.status, error?.code ?? "error", fields || error?.message || response.statusText);
  }
  return payload as T;
}

const json = (body: unknown) => JSON.stringify(body);

export const api = {
  me: () => request<User>("/api/me"),
  login: (email: string, password: string) => request<User>("/api/auth/login", { method: "POST", body: json({ email, password }) }),
  register: (name: string, email: string, password: string) => request<User>("/api/auth/register", { method: "POST", body: json({ name, email, password }) }),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),

  meta: () => request<Meta>("/api/meta"),
  dashboard: () => request<Dashboard>("/api/dashboard"),

  credentials: () => request<Credential[]>("/api/credentials"),
  createCredential: (body: { name: string; auth_type: string; secret: string; header_name?: string | null; username?: string | null }) =>
    request<Credential>("/api/credentials", { method: "POST", body: json(body) }),
  updateCredential: (id: number, body: Partial<{ name: string; secret: string; header_name: string; username: string }>) =>
    request<Credential>(`/api/credentials/${id}`, { method: "PATCH", body: json(body) }),
  deleteCredential: (id: number) => request<void>(`/api/credentials/${id}`, { method: "DELETE" }),

  integrations: () => request<Integration[]>("/api/integrations"),
  integration: (id: number) => request<Integration>(`/api/integrations/${id}`),
  createIntegration: (body: IntegrationInput) => request<Integration>("/api/integrations", { method: "POST", body: json(body) }),
  saveIntegration: (id: number, body: IntegrationInput) => request<Integration>(`/api/integrations/${id}`, { method: "PUT", body: json(body) }),
  patchIntegration: (id: number, body: Partial<{ enabled: boolean; schedule: string }>) =>
    request<Integration>(`/api/integrations/${id}`, { method: "PATCH", body: json(body) }),
  deleteIntegration: (id: number) => request<void>(`/api/integrations/${id}`, { method: "DELETE" }),
  runNow: (id: number) => request<RunSummary>(`/api/integrations/${id}/run`, { method: "POST" }),
  rotateWebhook: (id: number) => request<Integration>(`/api/integrations/${id}/rotate-webhook`, { method: "POST" }),

  testSource: (type: string, config: Record<string, unknown>, credential_id: number | null) =>
    request<TestResult>("/api/connections/test-source", { method: "POST", body: json({ type, config, credential_id }) }),
  testDestination: (type: string, config: Record<string, unknown>, credential_id: number | null) =>
    request<TestResult>("/api/connections/test-destination", { method: "POST", body: json({ type, config, credential_id }) }),
  previewMapping: (sample: Record<string, unknown>, mapping: MappingRule[]) =>
    request<{ ok: boolean; output: Record<string, unknown> | null; error: string | null }>("/api/mapping/preview", { method: "POST", body: json({ sample, mapping }) }),

  runs: (params: { integration_id?: number; status?: string; limit?: number } = {}) => {
    const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)])).toString();
    return request<RunSummary[]>(`/api/runs${q ? `?${q}` : ""}`);
  },
  run: (id: number) => request<RunDetail>(`/api/runs/${id}`),
  failures: (id: number) => request<FailedRecord[]>(`/api/runs/${id}/failures`),
};
