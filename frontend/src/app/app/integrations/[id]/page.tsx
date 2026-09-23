"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowRight, CircleAlert, Info, KeyRound, Loader2, MoreHorizontal, Pencil, Play, RefreshCw, Trash2, TriangleAlert } from "lucide-react";
import { toast } from "sonner";
import { FlowDiagram } from "@/components/app/flow";
import { RunsTable } from "@/components/app/runs-table";
import { CodeBlock, Empty, ErrorState, PageLoading, PageTitle, Panel, StatusBadge } from "@/components/app/ui";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Switch } from "@/components/ui/switch";
import { useApi } from "@/hooks/use-api";
import { useRunNow } from "@/hooks/use-run";
import { api } from "@/lib/api";
import { dateTime, host, SCHEDULE, timeAgo, timeUntil } from "@/lib/format";
import type { Credential, RunDetail } from "@/lib/types";
import { cn } from "@/lib/utils";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[110px_minmax(0,1fr)] gap-3 py-2 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words">{children}</dd>
    </div>
  );
}

function Auth({ credential }: { credential: Credential | null }) {
  if (!credential) return <span className="text-muted-foreground">None</span>;
  const kind = { bearer: "Bearer token", api_key: `API key · ${credential.header_name}`, basic: `Basic · ${credential.username}` }[credential.auth_type];
  return (
    <span className="flex items-start gap-1.5">
      <KeyRound className="mt-0.5 size-3.5 shrink-0 text-primary" />
      <span className="min-w-0">
        <span className="block">{credential.name}</span>
        <span className="block font-mono text-xs text-muted-foreground">{kind} · {credential.secret_hint}</span>
      </span>
    </span>
  );
}

const LEVEL = { info: Info, warning: TriangleAlert, error: CircleAlert } as const;

function RunLog({ run }: { run: RunDetail }) {
  return (
    <ol className="space-y-1.5 font-mono text-[12.5px]" aria-live="polite">
      {run.log.map((entry, i) => {
        const Icon = LEVEL[entry.level];
        return (
          <li key={i} className={cn("flex items-start gap-2", entry.level === "warning" && "text-warn", entry.level === "error" && "text-fail")}>
            <Icon className="mt-0.5 size-3.5 shrink-0" />{entry.message}
          </li>
        );
      })}
      {run.status === "running" ? (
        <li className="flex items-center gap-2 text-primary"><Loader2 className="size-3.5 animate-spin" />
          {run.stage === "send" ? `${run.records_processed} / ${run.records_read} processed…` : "working…"}
        </li>
      ) : null}
    </ol>
  );
}

export default function IntegrationPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const integration = useApi(() => api.integration(Number(id)), `integration-${id}`);
  const runner = useRunNow(Number(id), (run) => {
    integration.reload();
    if (run.status === "success") toast.success(`${run.records_successful} records synced`);
    else if (run.status === "partial") toast.warning(`${run.records_successful} synced · ${run.records_failed} failed`, { action: { label: "Inspect", onClick: () => router.push(`/app/runs/${run.id}`) } });
    else toast.error("Run failed", { description: run.error_summary ?? undefined });
  });

  if (integration.loading) return <PageLoading />;
  if (integration.error || !integration.data) return <ErrorState message={integration.error ?? "Integration not found."} onRetry={integration.reload} />;
  const data = integration.data;
  const sc = data.source_config as Record<string, unknown>;
  const dc = data.destination_config as Record<string, unknown>;
  const liveRun = runner.run ?? null;

  async function toggle(enabled: boolean) {
    try {
      integration.mutate(() => ({ ...data, enabled }));
      await api.patchIntegration(data.id, { enabled });
      integration.reload();
      toast.success(enabled ? "Integration enabled" : "Integration disabled");
    } catch (err) {
      toast.error((err as Error).message);
      integration.reload();
    }
  }

  async function remove() {
    if (!window.confirm(`Delete “${data.name}” and its run history?`)) return;
    await api.deleteIntegration(data.id);
    router.push("/app/integrations");
  }

  return (
    <>
      <PageTitle
        eyebrow={<Link href="/app/integrations" className="hover:text-foreground">Integrations</Link>}
        title={data.name}
        description={data.description ?? undefined}
        actions={
          <>
            <label className="flex items-center gap-2 rounded-lg border bg-card px-3 text-sm"><Switch checked={data.enabled} onCheckedChange={toggle} aria-label="Enabled" />{data.enabled ? "Enabled" : "Disabled"}</label>
            {data.source_type === "rest" ? (
              <Button onClick={runner.start} disabled={runner.starting || runner.running || data.running}>
                {runner.starting || runner.running ? <Loader2 className="animate-spin" /> : <Play />}Run now
              </Button>
            ) : null}
            <Button asChild variant="outline"><Link href={`/app/integrations/${data.id}/edit`}><Pencil />Edit</Link></Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild><Button variant="outline" size="icon" aria-label="More"><MoreHorizontal /></Button></DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {data.source_type === "webhook" ? <DropdownMenuItem onSelect={async () => { integration.mutate(() => data); const next = await api.rotateWebhook(data.id); integration.mutate(() => next); toast.success("New webhook URL generated — the old one stopped working."); }}><RefreshCw />Rotate webhook URL</DropdownMenuItem> : null}
                <DropdownMenuSeparator />
                <DropdownMenuItem variant="destructive" onSelect={remove}><Trash2 />Delete integration</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </>
        }
      />

      <FlowDiagram
        sourceType={data.source_type}
        sourceLabel={data.source_type === "webhook" ? "External app" : host(sc.url)}
        destinationType={data.destination_type}
        destinationLabel={host(dc.url)}
        method={String(dc.method ?? "POST")}
        run={liveRun ?? undefined}
      />

      {liveRun ? (
        <Panel title={liveRun.status === "running" ? "Running…" : `Run #${liveRun.id}`} action={liveRun.status !== "running" ? <Button asChild variant="ghost" size="sm"><Link href={`/app/runs/${liveRun.id}`}>Details<ArrowRight data-icon="inline-end" /></Link></Button> : <StatusBadge status="running" />} className="mt-4" bodyClassName="p-5">
          <RunLog run={liveRun} />
        </Panel>
      ) : null}

      {data.webhook_url ? (
        <Panel title="Webhook URL" description="POST JSON here to start a run. Treat it like a password — rotate it if it leaks." className="mt-4" bodyClassName="space-y-3 p-5">
          <CodeBlock value={data.webhook_url} copy />
          <CodeBlock value={`curl -X POST '${data.webhook_url}' \\\n  -H 'Content-Type: application/json' \\\n  -d '{"name": "Ana Costa", "email": "ana@example.com", "message": "Hi!"}'`} copy />
        </Panel>
      ) : null}

      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Panel title={data.source_type === "webhook" ? "Source · webhook" : "Source · REST API"} bodyClassName="px-5 py-2">
          <dl className="divide-y">
            {data.source_type === "rest" ? (
              <>
                <Row label="Request"><span className="font-mono text-[12.5px]"><span className="font-semibold text-primary">{String(sc.method)}</span> {String(sc.url)}</span></Row>
                <Row label="Records">{sc.records_path ? <code className="font-mono text-[12.5px]">{String(sc.records_path)}</code> : "Top-level list"}</Row>
                <Row label="Pages">{sc.pagination === "page" ? `?${sc.page_param}=1…${sc.max_pages}` : "Single request"}</Row>
                <Row label="Auth"><Auth credential={data.source_credential} /></Row>
              </>
            ) : (
              <>
                <Row label="Trigger">Inbound POST</Row>
                <Row label="Records">{sc.records_path ? <code className="font-mono text-[12.5px]">{String(sc.records_path)}</code> : "The body itself"}</Row>
              </>
            )}
          </dl>
        </Panel>
        <Panel title={`Mapping · ${data.mapping.length} fields`} bodyClassName="px-5 py-3">
          <ul className="space-y-1.5">
            {data.mapping.map((rule) => (
              <li key={rule.target} className="flex items-center gap-2 font-mono text-[12.5px]">
                <span className="truncate">{rule.source}</span>
                <ArrowRight className="size-3.5 shrink-0 text-muted-foreground" />
                <span className="truncate font-medium text-primary">{rule.target}</span>
                {rule.transform !== "none" ? <span className="ml-auto shrink-0 rounded bg-accent px-1.5 py-0.5 font-sans text-[11px] text-accent-foreground">{rule.transform}{rule.argument ? ` “${rule.argument}”` : ""}</span> : null}
                {rule.required ? <span className="shrink-0 text-primary" title="Required">*</span> : null}
              </li>
            ))}
          </ul>
        </Panel>
        <Panel title={data.destination_type === "webhook" ? "Destination · webhook" : "Destination · REST API"} bodyClassName="px-5 py-2">
          <dl className="divide-y">
            <Row label="Request"><span className="font-mono text-[12.5px]"><span className="font-semibold text-primary">{data.destination_type === "webhook" ? "POST" : String(dc.method)}</span> {String(dc.url)}</span></Row>
            <Row label={data.destination_type === "webhook" ? "Signing" : "Auth"}><Auth credential={data.destination_credential} /></Row>
            <Row label="Schedule">{data.source_type === "webhook" ? "On webhook" : SCHEDULE[data.schedule]}{data.next_run_at && data.enabled ? <span className="text-muted-foreground"> · next {timeUntil(data.next_run_at)}</span> : null}</Row>
            <Row label="Last run">{data.last_run_at ? <span title={dateTime(data.last_run_at)}>{timeAgo(data.last_run_at)}</span> : "Never"}</Row>
          </dl>
        </Panel>
      </div>

      <Panel title="Recent runs" className="mt-4" action={<Button asChild variant="ghost" size="sm"><Link href={`/app/runs?integration=${data.id}`}>All<ArrowRight data-icon="inline-end" /></Link></Button>}>
        {data.recent_runs.length ? <RunsTable runs={data.recent_runs} showIntegration={false} /> : <Empty title="No runs yet" description={data.source_type === "webhook" ? "Send a webhook to the URL above." : "Press Run now to sync."} />}
      </Panel>
    </>
  );
}
