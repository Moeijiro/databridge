"use client";

import { useState } from "react";
import { AlertTriangle, Check, Copy, RotateCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { STATUS } from "@/lib/format";
import type { RunStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

export function PageTitle({ title, description, actions, eyebrow }: { title: React.ReactNode; description?: React.ReactNode; actions?: React.ReactNode; eyebrow?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        {eyebrow ? <div className="mb-1.5 text-sm text-muted-foreground">{eyebrow}</div> : null}
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description ? <div className="mt-1 text-sm text-muted-foreground">{description}</div> : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}

export function Panel({ title, description, action, children, className, bodyClassName }: {
  title?: React.ReactNode; description?: React.ReactNode; action?: React.ReactNode; children: React.ReactNode; className?: string; bodyClassName?: string;
}) {
  return (
    <section className={cn("rounded-xl border bg-card shadow-[0_1px_2px_rgba(15,23,42,0.04)]", className)}>
      {title ? (
        <header className="flex items-start justify-between gap-3 border-b px-5 py-3.5">
          <div className="min-w-0">
            <h2 className="text-sm font-semibold">{title}</h2>
            {description ? <p className="mt-0.5 text-xs text-muted-foreground">{description}</p> : null}
          </div>
          {action}
        </header>
      ) : null}
      <div className={bodyClassName}>{children}</div>
    </section>
  );
}

export function Stat({ label, value, hint, color }: { label: string; value: React.ReactNode; hint?: React.ReactNode; color?: string }) {
  return (
    <div className="rounded-xl border bg-card px-5 py-4">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-2 text-3xl font-semibold tracking-tight tabular" style={color ? { color } : undefined}>{value}</p>
      {hint ? <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

export function StatusBadge({ status, className }: { status: RunStatus; className?: string }) {
  const { label, color } = STATUS[status];
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap", className)}
      style={{ color, borderColor: `color-mix(in oklch, ${color} 30%, transparent)`, background: `color-mix(in oklch, ${color} 9%, transparent)` }}>
      <span className={cn("size-1.5 rounded-full", status === "running" && "animate-pulse")} style={{ background: color }} />
      {label}
    </span>
  );
}

export function CodeBlock({ value, className, copy = false }: { value: unknown; className?: string; copy?: boolean }) {
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  const [copied, setCopied] = useState(false);
  return (
    <div className={cn("relative", className)}>
      <pre className="overflow-auto rounded-lg bg-code p-3.5 font-mono text-[12px] leading-relaxed text-code-foreground">{text}</pre>
      {copy ? (
        <button type="button" aria-label="Copy" onClick={async () => { await navigator.clipboard.writeText(text).catch(() => undefined); setCopied(true); setTimeout(() => setCopied(false), 1400); }}
          className="absolute top-2 right-2 rounded-md bg-white/10 p-1.5 text-code-foreground hover:bg-white/20">
          {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
        </button>
      ) : null}
    </div>
  );
}

export function Empty({ title, description, icon: Icon, action, className }: { title: string; description?: string; icon?: React.ComponentType<{ className?: string }>; action?: React.ReactNode; className?: string }) {
  return (
    <div className={cn("flex flex-col items-center justify-center px-6 py-12 text-center", className)}>
      {Icon ? <span className="mb-3 flex size-10 items-center justify-center rounded-full bg-accent"><Icon className="size-5 text-primary" /></span> : null}
      <p className="text-sm font-medium">{title}</p>
      {description ? <p className="mt-1 max-w-sm text-sm text-muted-foreground">{description}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center gap-3 rounded-xl border border-destructive/25 bg-destructive/5 px-6 py-10 text-center">
      <AlertTriangle className="size-5 text-destructive" />
      <p className="text-sm">{message}</p>
      {onRetry ? <Button variant="outline" size="sm" onClick={onRetry}><RotateCw />Try again</Button> : null}
    </div>
  );
}

export function PageLoading() {
  return (
    <div className="space-y-4" role="status" aria-label="Loading">
      <Skeleton className="h-8 w-64" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24 rounded-xl" />)}</div>
      <Skeleton className="h-72 rounded-xl" />
    </div>
  );
}

export function RowsLoading({ rows = 4 }: { rows?: number }) {
  return <div className="space-y-2 p-4" role="status" aria-label="Loading">{Array.from({ length: rows }, (_, i) => <Skeleton key={i} className="h-11 w-full" />)}</div>;
}
