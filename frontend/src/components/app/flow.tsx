"use client";

import { ArrowDownToLine, Braces, CheckCircle2, Globe, Send, Shuffle, Wand2, Webhook, XCircle } from "lucide-react";
import { motion } from "motion/react";
import type { ConnectorType, RunStatus, RunSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

type Stage = "idle" | "fetch" | "map" | "send" | "done";

interface Step {
  key: string;
  label: string;
  detail: string;
  icon: React.ComponentType<{ className?: string }>;
  stage: Exclude<Stage, "idle" | "done">;
}

/**
 * Source → Fetch → Map → Transform → Send → Destination, with the current
 * stage highlighted while a run is in progress and counts filled in as they arrive.
 */
export function FlowDiagram({
  sourceType,
  sourceLabel,
  destinationType,
  destinationLabel,
  method = "POST",
  run,
  className,
}: {
  sourceType: ConnectorType;
  sourceLabel: string;
  destinationType: ConnectorType;
  destinationLabel: string;
  method?: string;
  run?: RunSummary | null;
  className?: string;
}) {
  const stage: Stage = !run ? "idle" : run.status === "running" ? run.stage === "done" ? "send" : run.stage : "done";
  const status: RunStatus | null = run?.status ?? null;
  const steps: Step[] = [
    { key: "source", label: sourceType === "webhook" ? "Webhook in" : "REST API", detail: sourceLabel, icon: sourceType === "webhook" ? Webhook : Globe, stage: "fetch" },
    { key: "fetch", label: sourceType === "webhook" ? "Receive" : "Fetch", detail: run && run.records_read ? `${run.records_read} records` : "records", icon: ArrowDownToLine, stage: "fetch" },
    { key: "map", label: "Map", detail: "rename fields", icon: Shuffle, stage: "map" },
    { key: "transform", label: "Transform", detail: "convert values", icon: Wand2, stage: "map" },
    { key: "send", label: destinationType === "webhook" ? "POST webhook" : method, detail: run && run.records_processed ? `${run.records_successful} ok · ${run.records_failed} failed` : "with retries", icon: Send, stage: "send" },
    { key: "destination", label: destinationType === "webhook" ? "Webhook out" : "Destination API", detail: destinationLabel, icon: destinationType === "webhook" ? Webhook : Braces, stage: "send" },
  ];
  const order: Stage[] = ["fetch", "map", "send"];
  const stateOf = (step: Step): "idle" | "active" | "done" | "ok" | "fail" => {
    if (stage === "idle") return "idle";
    if (stage === "done") {
      if (status === "failed" && step.stage !== "fetch" && (run?.records_read ?? 0) === 0) return "idle";
      return status === "success" ? "ok" : status === "failed" ? "fail" : "done";
    }
    const current = order.indexOf(stage);
    const mine = order.indexOf(step.stage);
    return mine < current ? "done" : mine === current ? "active" : "idle";
  };

  return (
    <div className={cn("rounded-xl border bg-card p-4 sm:p-6", className)}>
      <ol className="grid grid-cols-1 gap-2 sm:grid-cols-6 sm:gap-0">
        {steps.map((step, index) => {
          const state = stateOf(step);
          const next = steps[index + 1];
          const lineActive = next && stage !== "done" && stage !== "idle" && (state === "active" || (state === "done" && stateOf(next) === "active"));
          return (
            <li key={step.key} className="relative flex items-center gap-3 sm:flex-col sm:gap-2 sm:text-center">
              <motion.span
                animate={state === "active" ? { scale: [1, 1.06, 1] } : { scale: 1 }}
                transition={state === "active" ? { duration: 1.2, repeat: Infinity } : { duration: 0.2 }}
                className={cn(
                  "relative z-10 flex size-11 shrink-0 items-center justify-center rounded-xl border-2 bg-card transition-colors",
                  state === "idle" && "border-border text-muted-foreground",
                  state === "active" && "border-primary bg-primary text-primary-foreground shadow-[0_0_0_6px_color-mix(in_oklch,var(--primary)_15%,transparent)]",
                  state === "done" && "border-primary/60 text-primary",
                  state === "ok" && "border-ok text-ok",
                  state === "fail" && "border-fail text-fail",
                )}
              >
                <step.icon className="size-5" />
              </motion.span>
              <span className="min-w-0 sm:px-1">
                <span className={cn("block text-sm font-medium", state === "active" && "text-primary")}>{step.label}</span>
                <span className="block truncate text-xs text-muted-foreground sm:max-w-[140px]" title={step.detail}>{step.detail}</span>
              </span>
              {next ? (
                <>
                  <span aria-hidden className={cn("absolute top-[22px] left-[calc(50%+26px)] hidden h-0.5 w-[calc(100%-52px)] sm:block", lineActive ? "flow-line-x" : "bg-border")} />
                  <span aria-hidden className={cn("absolute top-12 left-[21px] h-2 w-0.5 sm:hidden", lineActive ? "flow-line-y" : "bg-border")} />
                </>
              ) : null}
            </li>
          );
        })}
      </ol>
      {run && stage === "done" ? (
        <p className={cn("mt-4 flex items-center gap-2 text-sm", status === "success" ? "text-ok" : status === "failed" ? "text-fail" : "text-warn")}>
          {status === "success" ? <CheckCircle2 className="size-4" /> : <XCircle className="size-4" />}
          {status === "failed" && !run.records_read ? run.error_summary : `${run.records_successful} successful · ${run.records_failed} failed${run.retries ? ` · ${run.retries} retried` : ""}`}
        </p>
      ) : null}
    </div>
  );
}
