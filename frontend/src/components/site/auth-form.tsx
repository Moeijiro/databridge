"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";

const DEMO = { email: "demo@databridge.dev", password: "databridge-demo-1234" };

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const params = useSearchParams();
  const prefill = mode === "login" && params.get("demo") === "1";
  const [name, setName] = useState("");
  const [email, setEmail] = useState(prefill ? DEMO.email : "");
  const [password, setPassword] = useState(prefill ? DEMO.password : "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") await api.login(email, password);
      else await api.register(name, email, password);
      router.push("/app");
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center px-5 py-16">
      <div className="pointer-events-none absolute inset-0 bg-dots [mask-image:radial-gradient(ellipse_60%_50%_at_50%_40%,#000,transparent)]" aria-hidden />
      <main id="main" className="relative w-full max-w-sm">
        <Link href="/" className="mb-8 flex justify-center"><Logo /></Link>
        <div className="rounded-xl border bg-card p-6 shadow-sm">
          <h1 className="text-lg font-semibold">{mode === "login" ? "Sign in" : "Create your account"}</h1>
          {prefill ? <p className="mt-3 rounded-lg bg-accent px-3 py-2 text-xs text-accent-foreground">Demo credentials filled in. The demo integrations talk to built-in demo APIs.</p> : null}
          <form onSubmit={submit} className="mt-5 space-y-4">
            {mode === "register" ? <div className="space-y-2"><Label htmlFor="name">Name</Label><Input id="name" required maxLength={80} value={name} onChange={(e) => setName(e.target.value)} /></div> : null}
            <div className="space-y-2"><Label htmlFor="email">Email</Label><Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} required minLength={mode === "register" ? 10 : undefined} value={password} onChange={(e) => setPassword(e.target.value)} />
              {mode === "register" ? <p className="text-xs text-muted-foreground">At least 10 characters.</p> : null}
            </div>
            {error ? <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">{error}</p> : null}
            <Button type="submit" className="h-10 w-full" disabled={busy}>{busy ? <Loader2 className="animate-spin" /> : null}{mode === "login" ? "Sign in" : "Create account"}</Button>
          </form>
        </div>
        <p className="mt-5 text-center text-sm text-muted-foreground">
          {mode === "login" ? <>No account? <Link href="/register" className="font-medium text-primary hover:underline">Create one</Link> · <Link href="/login?demo=1" className="font-medium text-primary hover:underline">Use the demo</Link></>
            : <>Have an account? <Link href="/login" className="font-medium text-primary hover:underline">Sign in</Link></>}
        </p>
      </main>
    </div>
  );
}
