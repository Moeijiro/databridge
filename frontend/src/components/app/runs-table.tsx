import Link from "next/link";
import { StatusBadge } from "@/components/app/ui";
import { dateTime, duration, num, timeAgo } from "@/lib/format";
import type { RunSummary } from "@/lib/types";

const TRIGGER: Record<string, string> = { manual: "Run now", schedule: "Scheduled", webhook: "Webhook" };

export function RunsTable({ runs, showIntegration = true }: { runs: RunSummary[]; showIntegration?: boolean }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] text-sm">
        <thead>
          <tr className="border-b text-left text-xs text-muted-foreground">
            <th scope="col" className="px-5 py-2.5 font-medium">Run</th>
            {showIntegration ? <th scope="col" className="px-3 py-2.5 font-medium">Integration</th> : null}
            <th scope="col" className="px-3 py-2.5 font-medium">Status</th>
            <th scope="col" className="px-3 py-2.5 text-right font-medium">Read</th>
            <th scope="col" className="px-3 py-2.5 text-right font-medium">Sent</th>
            <th scope="col" className="px-3 py-2.5 text-right font-medium">Failed</th>
            <th scope="col" className="px-5 py-2.5 text-right font-medium">Duration</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {runs.map((run) => (
            <tr key={run.id} className="group hover:bg-accent/40">
              <td className="px-5 py-2.5">
                <Link href={`/app/runs/${run.id}`} className="font-medium group-hover:text-primary">#{run.id}</Link>
                <span className="ml-2 text-xs text-muted-foreground" title={dateTime(run.started_at)}>{TRIGGER[run.trigger]} · {timeAgo(run.started_at)}</span>
              </td>
              {showIntegration ? <td className="max-w-[260px] truncate px-3 py-2.5 text-muted-foreground">{run.integration_name}</td> : null}
              <td className="px-3 py-2.5"><StatusBadge status={run.status} /></td>
              <td className="px-3 py-2.5 text-right tabular">{num(run.records_read)}</td>
              <td className="px-3 py-2.5 text-right text-ok tabular">{num(run.records_successful)}</td>
              <td className="px-3 py-2.5 text-right tabular">{run.records_failed ? <span className="text-fail">{num(run.records_failed)}</span> : <span className="text-muted-foreground">0</span>}</td>
              <td className="px-5 py-2.5 text-right text-muted-foreground tabular">{duration(run.duration_ms)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
