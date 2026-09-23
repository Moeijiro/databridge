import { cn } from "@/lib/utils";

/** Two endpoints joined by a bridge arc. */
export function Logo({ className, wordmark = true }: { className?: string; wordmark?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <span className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground" aria-hidden>
        <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
          <circle cx="5" cy="16" r="2" fill="currentColor" />
          <circle cx="19" cy="16" r="2" fill="currentColor" />
          <path d="M5 16c0-6 14-6 14 0" />
        </svg>
      </span>
      {wordmark ? <span className="font-semibold tracking-tight">DataBridge</span> : null}
    </span>
  );
}
