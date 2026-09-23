import type { Metadata } from "next";
import { SessionGate } from "@/components/app/session";
import { AppShell } from "@/components/app/shell";

export const metadata: Metadata = { title: "App", robots: { index: false, follow: false } };

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionGate>
      <AppShell>{children}</AppShell>
    </SessionGate>
  );
}
