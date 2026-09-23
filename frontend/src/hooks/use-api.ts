"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface ApiState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
  mutate: (updater: (current: T) => T) => void;
}

/**
 * Loads data when `key` changes. The fetcher lives in a ref so dependency
 * arrays stay literal, and `reload` keeps the old data on screen while the
 * new request runs (no flash of skeletons after every action).
 */
export function useApi<T>(fetcher: () => Promise<T>, key: string): ApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [nonce, setNonce] = useState(0);
  const ref = useRef(fetcher);

  useEffect(() => {
    ref.current = fetcher;
  });

  useEffect(() => {
    let cancelled = false;
    ref
      .current()
      .then((value) => {
        if (cancelled) return;
        setData(value);
        setError(null);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [key, nonce]);

  const reload = useCallback(() => setNonce((value) => value + 1), []);
  const mutate = useCallback((updater: (current: T) => T) => setData((current) => (current === null ? current : updater(current))), []);

  return { data, error, loading, reload, mutate };
}
