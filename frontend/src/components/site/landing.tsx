"use client";

import Link from "next/link";
import { motion } from "motion/react";
import {
  ArrowRight,
  ArrowDownToLine,
  Braces,
  CalendarClock,
  FileWarning,
  Globe,
  KeyRound,
  Lock,
  RefreshCw,
  ScrollText,
  Send,
  ShieldCheck,
  Shuffle,
  Wand2,
  Webhook,
} from "lucide-react";
import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";

const ease = [0.22, 1, 0.36, 1] as const;

function Reveal({ children, delay = 0, className }: { children: React.ReactNode; delay?: number; className?: string }) {
  return <motion.div className={className} initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-60px" }} transition={{ duration: 0.5, delay, ease }}>{children}</motion.div>;
}

function Eyebrow({ children }: { children: React.ReactNode }) {
  return <p className="text-sm font-semibold text-primary">{children}</p>;
}

export function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/85 backdrop-blur">
      <nav aria-label="Main" className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-5 sm:px-8">
        <Link href="/" aria-label="DataBridge home"><Logo /></Link>
        <ul className="hidden gap-1 text-sm md:flex">
          {[["#how", "How it works"], ["#mapping", "Field mapping"], ["#reliability", "Reliability"], ["#use-cases", "Use cases"]].map(([h, l]) => (
            <li key={h}><a href={h} className="rounded-md px-3 py-1.5 text-muted-foreground hover:text-foreground">{l}</a></li>
          ))}
        </ul>
        <div className="ml-auto flex gap-2">
          <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex"><Link href="/login">Sign in</Link></Button>
          <Button asChild size="sm"><Link href="/login?demo=1">Open the demo</Link></Button>
        </div>
      </nav>
    </header>
  );
}

const FLOW = [
  { icon: Globe, label: "REST API", detail: "GET /customers" },
  { icon: ArrowDownToLine, label: "Fetch", detail: "43 records · 3 pages" },
  { icon: Shuffle, label: "Map", detail: "mail → email" },
  { icon: Wand2, label: "Transform", detail: '"42" → 42' },
  { icon: Send, label: "POST", detail: "3 retried" },
  { icon: Braces, label: "Destination", detail: "42 synced · 1 failed" },
];

function HeroFlow() {
  return (
    <div className="rounded-2xl border bg-card p-5 shadow-[0_24px_60px_-30px_rgba(30,50,120,0.35)] sm:p-7">
      <div className="mb-5 flex items-center justify-between">
        <span className="text-sm font-semibold">CRM customers → Marketing platform</span>
        <span className="rounded-full border border-run/30 bg-run/10 px-2 py-0.5 text-xs font-medium text-run">Running</span>
      </div>
      <ol className="grid grid-cols-3 gap-y-6 sm:grid-cols-6">
        {FLOW.map((step, i) => (
          <motion.li key={step.label} className="relative flex flex-col items-center gap-2 text-center"
            initial={{ opacity: 0.35 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 + i * 0.35, duration: 0.3 }}>
            <motion.span className="relative z-10 flex size-11 items-center justify-center rounded-xl border-2 bg-card text-muted-foreground"
              initial={{ borderColor: "var(--border)", color: "var(--muted-foreground)" }}
              animate={{ borderColor: "var(--primary)", color: "var(--primary)" }}
              transition={{ delay: 0.3 + i * 0.35, duration: 0.3 }}>
              <step.icon className="size-5" />
            </motion.span>
            <span className="text-sm font-medium">{step.label}</span>
            <span className="font-mono text-[11px] text-muted-foreground">{step.detail}</span>
            {i < FLOW.length - 1 ? (
              <motion.span aria-hidden className="absolute top-[22px] left-[calc(50%+26px)] hidden h-0.5 w-[calc(100%-52px)] origin-left bg-primary sm:block"
                initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ delay: 0.45 + i * 0.35, duration: 0.3 }} />
            ) : null}
          </motion.li>
        ))}
      </ol>
      <div className="mt-6 grid grid-cols-1 gap-2 font-mono text-[12px] sm:grid-cols-2">
        {["Fetching…", "43 records received", "Transforming…", "Sending…", "42 successful", "1 failed · Record #31 — Missing required field: email"].map((line, i) => (
          <motion.p key={line} className={i === 5 ? "text-fail sm:col-span-2" : i === 4 ? "text-ok" : "text-muted-foreground"}
            initial={{ opacity: 0, x: -4 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.6 + i * 0.3 }}>{i === 5 ? "✕" : "›"} {line}</motion.p>
        ))}
      </div>
    </div>
  );
}

export function Hero() {
  return (
    <section className="relative overflow-hidden border-b">
      <div className="pointer-events-none absolute inset-0 bg-dots [mask-image:radial-gradient(ellipse_70%_60%_at_50%_0%,#000,transparent)]" aria-hidden />
      <div className="relative mx-auto max-w-6xl px-5 pt-16 pb-20 sm:px-8 sm:pt-24">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease }} className="max-w-3xl">
          <Eyebrow>API integration & data sync</Eyebrow>
          <h1 className="mt-4 text-4xl leading-[1.05] font-semibold tracking-tight sm:text-6xl">Connect one API to another — and see every record move.</h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">
            DataBridge fetches records from a REST API or a webhook, maps and converts the fields, and delivers them to
            another API — on a schedule, with retries, and a run log that shows exactly which record failed and why.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button asChild size="lg" className="h-11 px-5"><Link href="/login?demo=1">Open the live demo<ArrowRight data-icon="inline-end" /></Link></Button>
            <Button asChild size="lg" variant="outline" className="h-11 px-5"><a href="#how">How it works</a></Button>
          </div>
          <p className="mt-3 text-xs text-muted-foreground">The demo syncs between built-in demo APIs — no external accounts needed.</p>
        </motion.div>
        <motion.div className="mt-14" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.15, ease }}>
          <HeroFlow />
        </motion.div>
      </div>
    </section>
  );
}

export function How() {
  const steps = [
    { icon: Globe, title: "Connect a source", body: "A REST endpoint (GET or POST, with page-number pagination) or a private webhook URL that any app can POST to." },
    { icon: Shuffle, title: "Map the fields", body: "Pick source fields, rename them, and convert values — text to numbers, yes/no to true/false, prefixes, nested paths." },
    { icon: Send, title: "Deliver", body: "POST, PUT or PATCH each record to a REST API, or send signed webhooks. Temporary errors are retried." },
    { icon: CalendarClock, title: "Run on a schedule", body: "Manual, every 15 minutes, hourly or daily. Every run is logged with counts and the records that failed." },
  ];
  return (
    <section id="how" className="scroll-mt-14 border-b py-20 sm:py-24">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Eyebrow>How it works</Eyebrow>
        <h2 className="mt-3 max-w-2xl text-3xl font-semibold tracking-tight">Configuration, not code</h2>
        <ol className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((s, i) => (
            <Reveal key={s.title} delay={i * 0.05}>
              <li className="h-full rounded-xl border bg-card p-5">
                <span className="flex items-center justify-between"><s.icon className="size-5 text-primary" /><span className="font-mono text-xs text-muted-foreground">0{i + 1}</span></span>
                <h3 className="mt-4 font-semibold">{s.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{s.body}</p>
              </li>
            </Reveal>
          ))}
        </ol>
      </div>
    </section>
  );
}

const MAP_ROWS = [
  ["first_name", "none", "name"],
  ["mail", "lowercase", "email"],
  ["age", "to_number", "age"],
  ["newsletter", "to_boolean", "subscribed"],
  ["address.city", "none", "location.city"],
];

export function Mapping() {
  return (
    <section id="mapping" className="scroll-mt-14 border-b bg-card/60 py-20 sm:py-24">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Eyebrow>Field mapping</Eyebrow>
        <h2 className="mt-3 max-w-2xl text-3xl font-semibold tracking-tight">Shape the data between two systems that disagree</h2>
        <p className="mt-3 max-w-2xl text-muted-foreground">A small, named set of transforms — no scripting language to learn, and nothing that can surprise you at 3 a.m.</p>
        <Reveal className="mt-12 grid grid-cols-1 items-center gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)_minmax(0,1fr)]">
          <pre className="rounded-xl bg-code p-4 font-mono text-[12.5px] leading-relaxed text-code-foreground">{`{
  "first_name": "John",
  "mail": "John@Example.com",
  "age": "42",
  "newsletter": "yes",
  "address": { "city": "Lisbon" }
}`}</pre>
          <div className="rounded-xl border bg-card p-4">
            {MAP_ROWS.map(([from, transform, to]) => (
              <div key={from} className="flex items-center gap-2 border-b py-2 font-mono text-[12.5px] last:border-b-0">
                <span className="w-28 truncate">{from}</span>
                <ArrowRight className="size-3.5 text-muted-foreground" />
                <span className={transform === "none" ? "w-24 text-muted-foreground" : "w-24 rounded bg-accent px-1.5 text-center text-accent-foreground"}>{transform === "none" ? "—" : transform}</span>
                <ArrowRight className="size-3.5 text-muted-foreground" />
                <span className="truncate font-medium text-primary">{to}</span>
              </div>
            ))}
          </div>
          <pre className="rounded-xl bg-code p-4 font-mono text-[12.5px] leading-relaxed text-code-foreground">{`{
  "name": "John",
  "email": "john@example.com",
  "age": 42,
  "subscribed": true,
  "location": { "city": "Lisbon" }
}`}</pre>
        </Reveal>
      </div>
    </section>
  );
}

export function Reliability() {
  const items = [
    { icon: RefreshCw, title: "Retries that know the difference", body: "Timeouts, network errors, 429 and 5xx are retried with exponential back-off. A 400 isn't — it won't fix itself." },
    { icon: FileWarning, title: "Failed records you can inspect", body: "Record #31 · Destination returned 400 · Missing required field: email. Personal values in the preview are hidden." },
    { icon: ScrollText, title: "A log for every run", body: "Read, transformed, sent, failed, retried — with the stage it reached and how long it took." },
    { icon: Webhook, title: "Webhooks both ways", body: "Receive at a private URL; send signed deliveries (HMAC-SHA256) the receiver can verify." },
    { icon: KeyRound, title: "Credentials stay secret", body: "Encrypted at rest, referenced by id, never returned by the API — only ••••3456." },
    { icon: ShieldCheck, title: "SSRF-safe requests", body: "Private and cloud-metadata addresses are refused, redirects aren't followed, responses are size-capped." },
  ];
  return (
    <section id="reliability" className="scroll-mt-14 border-b py-20 sm:py-24">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Eyebrow>Reliability & security</Eyebrow>
        <h2 className="mt-3 max-w-2xl text-3xl font-semibold tracking-tight">Built for the day the other API has a bad day</h2>
        <div className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((it, i) => (
            <Reveal key={it.title} delay={i * 0.04}>
              <div className="h-full rounded-xl border bg-card p-5">
                <it.icon className="size-5 text-primary" />
                <h3 className="mt-4 font-semibold">{it.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{it.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

export function UseCases() {
  const cases = [
    ["CRM → email marketing", "New and updated contacts pushed to the mailing tool every hour, with consent flags converted to booleans."],
    ["Shop → accounting", "Orders sent to the bookkeeping API daily, with amounts as numbers and paid status as true/false."],
    ["Forms → team chat", "Website form submissions forwarded as signed webhooks the moment they arrive."],
    ["Legacy API → modern backend", "Old field names and string-typed values reshaped into the schema the new service expects."],
  ];
  return (
    <section id="use-cases" className="scroll-mt-14 py-20 sm:py-24">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Eyebrow>Use cases</Eyebrow>
        <h2 className="mt-3 max-w-2xl text-3xl font-semibold tracking-tight">Where two tools need to talk</h2>
        <div className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {cases.map(([title, body], i) => (
            <Reveal key={title} delay={i * 0.05}>
              <div className="h-full rounded-xl border bg-card p-6">
                <h3 className="font-semibold">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{body}</p>
              </div>
            </Reveal>
          ))}
        </div>
        <Reveal className="mt-16 rounded-2xl bg-primary px-6 py-14 text-center text-primary-foreground sm:px-12">
          <h2 className="mx-auto max-w-2xl text-3xl font-semibold tracking-tight">Watch a sync run end to end</h2>
          <p className="mx-auto mt-3 max-w-lg text-primary-foreground/80">The demo workspace has three integrations wired to built-in APIs — press Run now and follow it.</p>
          <Button asChild size="lg" variant="secondary" className="mt-8 h-11 px-5"><Link href="/login?demo=1">Open the demo<ArrowRight data-icon="inline-end" /></Link></Button>
        </Reveal>
      </div>
    </section>
  );
}

export function Footer() {
  return (
    <footer className="border-t">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-5 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-8">
        <Logo />
        <p className="text-xs">A portfolio project · MIT licensed · demo data is generated</p>
        <span className="flex items-center gap-1.5 text-xs"><Lock className="size-3.5" />Credentials encrypted at rest</span>
      </div>
    </footer>
  );
}
