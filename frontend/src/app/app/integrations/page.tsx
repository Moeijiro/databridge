"use client";

import Link from "next/link";
import { ArrowRight, Clock, Globe, Plus, Webhook, Workflow } from "lucide-react";
import { Empty, ErrorState, PageLoading, PageTitle, StatusBadge } from "@/components/app/ui";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import { api } from "@/lib/api";
import { host, SCHEDULE, timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function IntegrationsPage() {
  const list = useApi(() => api.integrations(), "integrations");
  if (list.loading) return <PageLoading />;
  if (list.error || !list.data) return <ErrorState message={list.error ?? "Couldn't load integrations."} onRetry={list.reload} />;
  const add = <Button asChild><Link href="/app/integrations/new"><Plus />New integration</Link></Button>;

  return (
    <>
      <PageTitle title="Integrations" description="Each one moves records from a source to a destination." actions={add} />
      {list.data.length ? (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {list.data.map((i) => {
            const SourceIcon = i.source_type === "webhook" ? Webhook : Globe;
            const DestIcon = i.destination_type === "webhook" ? Webhook : Globe;
            return (
              <Link key={i.id} href={`/app/integrations/${i.id}`} className={cn("group rounded-xl border bg-card p-5 transition-colors hover:border-primary/40", !i.enabled && "opacity-70")}>
                <div className="flex items-start justify-between gap-3">
                  <h2 className="font-semibold group-hover:text-primary">{i.name}</h2>
                  {i.last_run_status ? <StatusBadge status={i.last_run_status} /> : <span className="text-xs text-muted-foreground">Never run</span>}
                </div>
                <div className="mt-4 flex items-center gap-2 text-sm">
                  <span className="flex min-w-0 items-center gap-1.5 rounded-md border bg-muted/60 px-2 py-1"><SourceIcon className="size-3.5 shrink-0 text-primary" /><span className="truncate font-mono text-[12px]">{i.source_type === "webhook" ? "Webhook" : host(i.source_config.url)}</span></span>
                  <ArrowRight className="size-4 shrink-0 text-muted-foreground" />
                  <span className="flex min-w-0 items-center gap-1.5 rounded-md border bg-muted/60 px-2 py-1"><DestIcon className="size-3.5 shrink-0 text-primary" /><span className="truncate font-mono text-[12px]">{host(i.destination_config.url)}</span></span>
                </div>
                <p className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1"><Clock className="size-3.5" />{i.source_type === "webhook" ? "On webhook" : SCHEDULE[i.schedule]}</span>
                  <span>{i.mapping.length} mapped fields</span>
                  <span>Last run {timeAgo(i.last_run_at)}</span>
                  {!i.enabled ? <span className="font-medium text-warn">Disabled</span> : null}
                </p>
              </Link>
            );
          })}
        </div>
      ) : (
        <div className="rounded-xl border border-dashed bg-card"><Empty icon={Workflow} title="No integrations yet" description="Connect a source API to a destination and map the fields between them." action={add} /></div>
      )}
    </>
  );
}
