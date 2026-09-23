export type RunStatus = "running" | "success" | "partial" | "failed";
export type Schedule = "manual" | "15m" | "hourly" | "daily";
export type AuthType = "bearer" | "api_key" | "basic";
export type ConnectorType = "rest" | "webhook";

export interface User { id: number; email: string; name: string; is_demo: boolean }

export interface Credential {
  id: number;
  name: string;
  auth_type: AuthType;
  header_name: string | null;
  username: string | null;
  secret_hint: string | null;
  last_used_at: string | null;
  created_at: string;
  used_by: number;
}

export interface MappingRule {
  source: string;
  target: string;
  transform: string;
  argument: string | null;
  required: boolean;
  default: string | null;
}

export interface RunSummary {
  id: number;
  integration_id: number;
  integration_name: string | null;
  trigger: "manual" | "schedule" | "webhook";
  status: RunStatus;
  stage: "fetch" | "map" | "send" | "done";
  started_at: string;
  finished_at: string | null;
  records_read: number;
  records_processed: number;
  records_successful: number;
  records_failed: number;
  retries: number;
  error_summary: string | null;
  duration_ms: number | null;
}

export interface RunDetail extends RunSummary {
  log: { at: string; level: "info" | "warning" | "error"; message: string }[];
}

export interface FailedRecord {
  id: number;
  record_index: number;
  stage: "transform" | "send";
  status_code: number | null;
  error: string;
  attempts: number;
  preview: Record<string, unknown>;
}

export interface Integration {
  id: number;
  name: string;
  description: string | null;
  source_type: ConnectorType;
  source_config: Record<string, unknown>;
  source_credential: Credential | null;
  destination_type: ConnectorType;
  destination_config: Record<string, unknown>;
  destination_credential: Credential | null;
  mapping: MappingRule[];
  schedule: Schedule;
  enabled: boolean;
  webhook_url: string | null;
  last_run_at: string | null;
  last_run_status: RunStatus | null;
  next_run_at: string | null;
  created_at: string;
  updated_at: string;
  running: boolean;
  recent_runs: RunSummary[];
}

export interface IntegrationInput {
  name: string;
  description?: string | null;
  source_type: ConnectorType;
  source_config: Record<string, unknown>;
  source_credential_id: number | null;
  destination_type: ConnectorType;
  destination_config: Record<string, unknown>;
  destination_credential_id: number | null;
  mapping: MappingRule[];
  schedule: Schedule;
  enabled: boolean;
}

export interface TestResult {
  ok: boolean;
  message: string;
  status: number | null;
  elapsed_ms: number | null;
  details: { records?: number; fields?: string[]; sample?: Record<string, unknown> | null };
}

export interface Meta {
  transforms: { name: string; label: string; needs_argument: boolean; argument_label: string | null }[];
  schedules: { value: Schedule; label: string }[];
  demo: Record<string, string>;
}

export interface Dashboard {
  stats: {
    active_integrations: number;
    total_integrations: number;
    successful_syncs: number;
    partial_syncs: number;
    failed_syncs: number;
    records_processed: number;
    records_successful: number;
    records_failed: number;
  };
  days: { day: string; successful: number; failed: number }[];
  recent_runs: RunSummary[];
}
