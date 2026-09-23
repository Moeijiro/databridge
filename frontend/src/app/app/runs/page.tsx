"use client";

import { Suspense } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { History } from "lucide-react";
import { RunsTable } from "@/components/app/runs-table";
import { Empty, ErrorState, PageTitle, Panel, RowsLoading } from "@/components/app/ui";
import { useApi } from "@/hooks/use-api";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const FILTERS = [["", "All"], ["success", "Success"], ["partial", "Partial"], ["failed", "Failed"]] as const;

function Runs() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const status = params.get("status") ?? "";
  const integration = params.get("integration");
  const runs = useApi(() => api.runs({ status: status || undefined, integration_id: integration ? Number(integration) : undefined, limit: 100 }), `runs-${status}-${integration}`);
  const set = (value: string) => {
    const next = new URLSearchParams(params.toString());
    if (value) next.set("status", value);
    else next.delete("status");
    router.replace(`${pathname}?${next.toString()}`);
  };
  return (
    <>
      <PageTitle title="Sync runs" description="Every run with its counts. Open one to see the log and inspect failed records." />
      <Panel
        title={integration ? "Runs for one integration" : "All runs"}
        action={
          <div className="flex gap-1" role="tablist">
            {FILTERS.map(([value, label]) => (
              <button key={value} role="tab" aria-selected={status === value} onClick={() => set(value)}
                className={cn("rounded-md px-2.5 py-1 text-xs", status === value ? "bg-accent font-medium text-primary" : "text-muted-foreground hover:text-foreground")}>{label}</button>
            ))}
          </div>
        }
      >
        {runs.loading ? <RowsLoading /> : runs.error ? <div className="p-5"><ErrorState message={runs.error} /></div> : runs.data?.length ? <RunsTable runs={runs.data} /> : <Empty icon={History} title="No runs match" />}
      </Panel>
    </>
  );
}

export default function RunsPage() {
  return <Suspense><Runs /></Suspense>;
}
