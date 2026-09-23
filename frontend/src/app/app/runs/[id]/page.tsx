"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ChevronDown, CircleAlert, Info, ShieldCheck, TriangleAlert } from "lucide-react";
import { CodeBlock, Empty, ErrorState, PageLoading, PageTitle, Panel, Stat, StatusBadge } from "@/components/app/ui";
import { useApi } from "@/hooks/use-api";
import { api } from "@/lib/api";
import { dateTime, duration, num } from "@/lib/format";
import { cn } from "@/lib/utils";

const LEVEL = { info: Info, warning: TriangleAlert, error: CircleAlert } as const;

export default function RunPage() {
  const { id } = useParams<{ id: string }>();
  const run = useApi(() => api.run(Number(id)), `run-${id}`);
  const failures = useApi(() => api.failures(Number(id)), `failures-${id}`);
  const [open, setOpen] = useState<number | null>(null);

  if (run.loading) return <PageLoading />;
  if (run.error || !run.data) return <ErrorState message={run.error ?? "Run not found."} />;
  const r = run.data;

  return (
    <>
      <PageTitle
        eyebrow={<Link href={`/app/integrations/${r.integration_id}`} className="hover:text-foreground">{r.integration_name}</Link>}
        title={<span className="flex items-center gap-3">Run #{r.id} <StatusBadge status={r.status} /></span>}
        description={`${{ manual: "Started with Run now", schedule: "Scheduled run", webhook: "Triggered by a webhook" }[r.trigger]} · ${dateTime(r.started_at)} · ${duration(r.duration_ms)}`}
      />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Records read" value={num(r.records_read)} />
        <Stat label="Successful" value={num(r.records_successful)} color="var(--ok)" />
        <Stat label="Failed" value={num(r.records_failed)} color={r.records_failed ? "var(--fail)" : undefined} />
        <Stat label="Retries" value={num(r.retries)} hint="temporary failures recovered" />
      </div>
      {r.error_summary ? <p role="alert" className="mt-4 rounded-xl border border-fail/30 bg-fail/5 px-4 py-3 text-sm text-fail">{r.error_summary}</p> : null}

      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)]">
        <Panel title="Log" bodyClassName="p-5">
          <ol className="space-y-2 font-mono text-[12.5px]">
            {r.log.map((entry, i) => {
              const Icon = LEVEL[entry.level];
              return (
                <li key={i} className={cn("grid grid-cols-[64px_16px_minmax(0,1fr)] gap-2", entry.level === "warning" && "text-warn", entry.level === "error" && "text-fail")}>
                  <span className="text-muted-foreground">{new Date(entry.at).toLocaleTimeString("en-GB")}</span>
                  <Icon className="mt-0.5 size-3.5" />
                  <span>{entry.message}</span>
                </li>
              );
            })}
          </ol>
        </Panel>
        <Panel title={`Failed records · ${failures.data?.length ?? 0}`} description="Personal and secret-looking values are hidden; the full payload is never stored.">
          {failures.data?.length ? (
            <ul className="divide-y">
              {failures.data.map((f) => (
                <li key={f.id}>
                  <button type="button" onClick={() => setOpen(open === f.id ? null : f.id)} aria-expanded={open === f.id}
                    className="flex w-full items-start gap-3 px-5 py-3 text-left hover:bg-accent/40">
                    <span className="font-mono text-sm font-medium">#{f.record_index}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm">{f.error}</span>
                      <span className="mt-0.5 block text-xs text-muted-foreground">
                        {f.stage === "transform" ? "Failed while transforming — nothing was sent" : `${f.status_code ? `HTTP ${f.status_code}` : "No response"} · ${f.attempts} attempt${f.attempts === 1 ? "" : "s"}`}
                      </span>
                    </span>
                    <ChevronDown className={cn("mt-0.5 size-4 text-muted-foreground transition-transform", open === f.id && "rotate-180")} />
                  </button>
                  {open === f.id ? (
                    <div className="px-5 pb-4">
                      <p className="mb-2 flex items-center gap-1.5 text-xs text-muted-foreground"><ShieldCheck className="size-3.5 text-ok" />Source record, masked</p>
                      <CodeBlock value={f.preview} />
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <Empty title="No failed records" description="Every record in this run was delivered." />
          )}
        </Panel>
      </div>
    </>
  );
}
