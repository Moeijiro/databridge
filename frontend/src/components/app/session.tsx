"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { User } from "@/lib/types";

const SessionContext = createContext<User | null>(null);

export function useSession(): User {
  const user = useContext(SessionContext);
  if (!user) throw new Error("useSession must be used inside <SessionGate>");
  return user;
}

export function SessionGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.me()
      .then((me) => !cancelled && setUser(me))
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
        else setError((err as Error).message);
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (error) return <div className="flex min-h-screen items-center justify-center p-6 text-sm text-muted-foreground">{error}</div>;
  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground" role="status">
        <Loader2 className="size-5 animate-spin" aria-hidden />
        <span className="sr-only">Loading</span>
      </div>
    );
  }
  return <SessionContext.Provider value={user}>{children}</SessionContext.Provider>;
}
