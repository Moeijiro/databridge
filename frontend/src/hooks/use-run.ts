"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { RunDetail } from "@/lib/types";

/** Start a run and follow it: polls the run every 400 ms until it finishes. */
export function useRunNow(integrationId: number, onFinished?: (run: RunDetail) => void) {
  const [run, setRun] = useState<RunDetail | null>(null);
  const [starting, setStarting] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const finished = useRef(onFinished);
  useEffect(() => {
    finished.current = onFinished;
  });
  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  const follow = useCallback((runId: number) => {
    const poll = async () => {
      try {
        const next = await api.run(runId);
        setRun(next);
        if (next.status === "running") timer.current = setTimeout(poll, 400);
        else finished.current?.(next);
      } catch {
        timer.current = setTimeout(poll, 1500);
      }
    };
    poll();
  }, []);

  const start = useCallback(async () => {
    setStarting(true);
    try {
      const started = await api.runNow(integrationId);
      setRun({ ...started, log: [] });
      follow(started.id);
    } catch (err) {
      toast.error("Couldn't start the run", { description: (err as Error).message });
    } finally {
      setStarting(false);
    }
  }, [integrationId, follow]);

  return { run, start, starting, running: run?.status === "running" };
}
