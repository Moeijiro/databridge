import type { RunStatus, Schedule } from "./types";

const relative = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "never";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 0) return timeUntil(iso);
  if (s < 45) return "just now";
  if (s < 3600) return relative.format(-Math.round(s / 60), "minute");
  if (s < 86_400) return relative.format(-Math.round(s / 3600), "hour");
  return relative.format(-Math.round(s / 86_400), "day");
}

export function timeUntil(iso: string | null | undefined): string {
  if (!iso) return "—";
  const s = (new Date(iso).getTime() - Date.now()) / 1000;
  if (s <= 30) return "any moment";
  if (s < 3600) return relative.format(Math.round(s / 60), "minute");
  if (s < 86_400) return relative.format(Math.round(s / 3600), "hour");
  return relative.format(Math.round(s / 86_400), "day");
}

export function dateTime(iso: string | null | undefined): string {
  return iso ? new Date(iso).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" }) : "—";
}

export function duration(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(ms < 10_000 ? 1 : 0)} s`;
}

export function num(n: number): string {
  return n.toLocaleString("en");
}

export const STATUS: Record<RunStatus, { label: string; color: string }> = {
  running: { label: "Running", color: "var(--run)" },
  success: { label: "Success", color: "var(--ok)" },
  partial: { label: "Partial", color: "var(--warn)" },
  failed: { label: "Failed", color: "var(--fail)" },
};

export const SCHEDULE: Record<Schedule, string> = { manual: "Manual", "15m": "Every 15 min", hourly: "Hourly", daily: "Daily" };

export function host(url: unknown): string {
  try {
    const u = new URL(String(url));
    return `${u.host}${u.pathname}`;
  } catch {
    return String(url ?? "");
  }
}
