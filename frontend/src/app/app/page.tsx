"use client";

import Link from "next/link";
import { ArrowRight, History, Plus } from "lucide-react";
import { RunsTable } from "@/components/app/runs-table";
import { useSession } from "@/components/app/session";
import { Empty, ErrorState, PageLoading, PageTitle, Panel, Stat } from "@/components/app/ui";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import { api } from "@/lib/api";
import { num } from "@/lib/format";

export default function DashboardPage() {
  const user = useSession();
  const dashboard = useApi(() => api.dashboard(), "dashboard");
  if (dashboard.loading) return <PageLoading />;
  if (dashboard.error || !dashboard.data) return <ErrorState message={dashboard.error ?? "Couldn't load the dashboard."} onRetry={dashboard.reload} />;
  const { stats, days, recent_runs } = dashboard.data;
  const max = Math.max(1, ...days.map((d) => d.successful + d.failed));

  return (
    <>
      <PageTitle
        title={`Welcome back, ${user.name.split(" ")[0]}`}
        description="Sync activity across your integrations over the last 7 days."
        actions={<Button asChild><Link href="/app/integrations/new"><Plus />New integration</Link></Button>}
      />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Active integrations" value={stats.active_integrations} hint={`of ${stats.total_integrations}`} />
        <Stat label="Successful syncs" value={stats.successful_syncs} hint={`${stats.partial_syncs} partial`} color="var(--ok)" />
        <Stat label="Failed syncs" value={stats.failed_syncs} hint="the run itself failed" color={stats.failed_syncs ? "var(--fail)" : undefined} />
        <Stat label="Records processed" value={num(stats.records_processed)} hint={`${num(stats.records_failed)} failed`} />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <Panel title="Records per day" description="Delivered vs failed" className="self-start" bodyClassName="p-5">
          <div className="flex h-40 items-end gap-2" role="img" aria-label="Records delivered and failed per day">
            {days.map((d) => (
              <div key={d.day} className="group relative flex h-full flex-1 flex-col justify-end" title={`${d.day}: ${d.successful} delivered, ${d.failed} failed`}>
                {d.failed ? <span className="w-full rounded-t bg-fail/80" style={{ height: `${(d.failed / max) * 100}%` }} /> : null}
                <span className={d.failed ? "w-full bg-primary/80" : "w-full rounded-t bg-primary/80"} style={{ height: `${Math.max((d.successful / max) * 100, d.successful ? 2 : 0)}%` }} />
                {!d.successful && !d.failed ? <span className="h-px w-full bg-border" /> : null}
              </div>
            ))}
          </div>
          <div className="mt-2 flex justify-between text-[11px] text-muted-foreground">
            {days.map((d) => <span key={d.day} className="flex-1 text-center">{new Date(`${d.day}T12:00:00`).toLocaleDateString("en", { weekday: "short" })}</span>)}
          </div>
        </Panel>
        <Panel title="Recent runs" action={<Button asChild variant="ghost" size="sm"><Link href="/app/runs">All runs<ArrowRight data-icon="inline-end" /></Link></Button>}>
          {recent_runs.length ? <RunsTable runs={recent_runs} /> : <Empty icon={History} title="No runs yet" description="Create an integration and press Run now." />}
        </Panel>
      </div>
    </>
  );
}
