"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { CheckCircle2, FlaskConical, Globe, Loader2, PlugZap, Webhook, XCircle } from "lucide-react";
import { toast } from "sonner";
import { EMPTY_RULE, MappingEditor } from "@/components/app/mapping-editor";
import { Panel } from "@/components/app/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useApi } from "@/hooks/use-api";
import { api } from "@/lib/api";
import type { ConnectorType, Integration, IntegrationInput, MappingRule, Schedule, TestResult } from "@/lib/types";
import { cn } from "@/lib/utils";

const NONE = "__none__";

function toLines(record: unknown, sep: string): string {
  return Object.entries((record as Record<string, string>) ?? {}).map(([k, v]) => `${k}${sep}${v}`).join("\n");
}

function fromLines(text: string, sep: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const line of text.split("\n")) {
    const at = line.indexOf(sep);
    if (at > 0) out[line.slice(0, at).trim()] = line.slice(at + sep.length).trim();
  }
  return out;
}

function TypeToggle({ value, onChange, label }: { value: ConnectorType; onChange: (value: ConnectorType) => void; label: string }) {
  return (
    <div className="inline-flex rounded-lg border bg-muted/60 p-0.5" role="radiogroup" aria-label={label}>
      {([["rest", "REST API", Globe], ["webhook", "Webhook", Webhook]] as const).map(([v, text, Icon]) => (
        <button key={v} type="button" role="radio" aria-checked={value === v} onClick={() => onChange(v)}
          className={cn("flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors", value === v ? "bg-card font-medium shadow-sm" : "text-muted-foreground hover:text-foreground")}>
          <Icon className="size-3.5" />{text}
        </button>
      ))}
    </div>
  );
}

function TestBadge({ result }: { result: TestResult | null }) {
  if (!result) return null;
  return (
    <div className={cn("mt-3 rounded-lg border px-3.5 py-2.5 text-sm", result.ok ? "border-ok/30 bg-ok/5" : "border-fail/30 bg-fail/5")} role="status">
      <p className={cn("flex items-center gap-2 font-medium", result.ok ? "text-ok" : "text-fail")}>
        {result.ok ? <CheckCircle2 className="size-4" /> : <XCircle className="size-4" />}
        {result.ok ? "Connected" : "Failed"}
        {result.status ? <span className="font-mono text-xs">HTTP {result.status}</span> : null}
        {result.elapsed_ms != null ? <span className="font-mono text-xs text-muted-foreground">{result.elapsed_ms} ms</span> : null}
      </p>
      <p className="mt-0.5 text-muted-foreground">{result.message}</p>
      {result.details.fields?.length ? (
        <p className="mt-1.5 font-mono text-[11.5px] text-muted-foreground">fields: {result.details.fields.join(", ")}</p>
      ) : null}
    </div>
  );
}

function CredentialSelect({ value, onChange, id }: { value: number | null; onChange: (v: number | null) => void; id: string }) {
  const credentials = useApi(() => api.credentials(), "credentials");
  return (
    <Select value={value ? String(value) : NONE} onValueChange={(v) => onChange(v === NONE ? null : Number(v))}>
      <SelectTrigger id={id} className="w-full"><SelectValue /></SelectTrigger>
      <SelectContent>
        <SelectItem value={NONE}>No authentication</SelectItem>
        {credentials.data?.map((c) => (
          <SelectItem key={c.id} value={String(c.id)}>{c.name} <span className="font-mono text-xs text-muted-foreground">{c.secret_hint}</span></SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export function IntegrationForm({ initial }: { initial?: Integration }) {
  const router = useRouter();
  const meta = useApi(() => api.meta(), "meta");
  const sc = (initial?.source_config ?? {}) as Record<string, unknown>;
  const dc = (initial?.destination_config ?? {}) as Record<string, unknown>;

  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [sourceType, setSourceType] = useState<ConnectorType>(initial?.source_type ?? "rest");
  const [sourceUrl, setSourceUrl] = useState(String(sc.url ?? ""));
  const [sourceMethod, setSourceMethod] = useState(String(sc.method ?? "GET"));
  const [recordsPath, setRecordsPath] = useState(String(sc.records_path ?? ""));
  const [pagination, setPagination] = useState(String(sc.pagination ?? "none"));
  const [pageParam, setPageParam] = useState(String(sc.page_param ?? "page"));
  const [maxPages, setMaxPages] = useState(Number(sc.max_pages ?? 10));
  const [params, setParams] = useState(toLines(sc.params, "="));
  const [sourceHeaders, setSourceHeaders] = useState(toLines(sc.headers, ": "));
  const [sourceCredential, setSourceCredential] = useState<number | null>(initial?.source_credential?.id ?? null);

  const [destinationType, setDestinationType] = useState<ConnectorType>(initial?.destination_type ?? "rest");
  const [destinationUrl, setDestinationUrl] = useState(String(dc.url ?? ""));
  const [destinationMethod, setDestinationMethod] = useState(String(dc.method ?? "POST"));
  const [destinationHeaders, setDestinationHeaders] = useState(toLines(dc.headers, ": "));
  const [destinationCredential, setDestinationCredential] = useState<number | null>(initial?.destination_credential?.id ?? null);

  const [mapping, setMapping] = useState<MappingRule[]>(initial?.mapping?.length ? initial.mapping : [{ ...EMPTY_RULE }]);
  const [schedule, setSchedule] = useState<Schedule>(initial?.schedule ?? "manual");
  const [enabled, setEnabled] = useState(initial?.enabled ?? true);

  const [sourceTest, setSourceTest] = useState<TestResult | null>(null);
  const [destinationTest, setDestinationTest] = useState<TestResult | null>(null);
  const [testing, setTesting] = useState<"source" | "destination" | null>(null);
  const [sample, setSample] = useState<Record<string, unknown> | null>(null);
  const [saving, setSaving] = useState(false);

  const sourceConfig = () =>
    sourceType === "rest"
      ? { url: sourceUrl, method: sourceMethod, records_path: recordsPath, pagination, page_param: pageParam, max_pages: maxPages,
          params: fromLines(params, "="), headers: fromLines(sourceHeaders, ":") }
      : { records_path: recordsPath };
  const destinationConfig = () =>
    destinationType === "rest"
      ? { url: destinationUrl, method: destinationMethod, headers: fromLines(destinationHeaders, ":") }
      : { url: destinationUrl, headers: fromLines(destinationHeaders, ":") };

  async function test(kind: "source" | "destination") {
    setTesting(kind);
    try {
      if (kind === "source") {
        const result = await api.testSource(sourceType, sourceConfig(), sourceCredential);
        setSourceTest(result);
        if (result.details.sample) setSample(result.details.sample);
      } else {
        setDestinationTest(await api.testDestination(destinationType, destinationConfig(), destinationCredential));
      }
    } catch (err) {
      const result = { ok: false, message: (err as Error).message, status: null, elapsed_ms: null, details: {} };
      if (kind === "source") setSourceTest(result);
      else setDestinationTest(result);
    } finally {
      setTesting(null);
    }
  }

  async function useDemo() {
    const demo = meta.data?.demo;
    if (!demo) return;
    const creds = await api.credentials().catch(() => []);
    setName((n) => n || "Customers → Marketing (demo)");
    setSourceType("rest");
    setSourceUrl(demo.source_customers);
    setRecordsPath("data");
    setPagination("page");
    setParams("per_page=20");
    setSourceCredential(creds.find((c) => c.auth_type === "bearer" && c.name.toLowerCase().includes("crm"))?.id ?? null);
    setDestinationType("rest");
    setDestinationUrl(demo.destination_customers);
    setDestinationMethod("POST");
    setDestinationCredential(creds.find((c) => c.auth_type === "api_key")?.id ?? null);
    toast.info("Filled in the demo APIs", { description: "Run “Test source” to load a sample record for the mapping." });
  }

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    const body: IntegrationInput = {
      name, description: description || null,
      source_type: sourceType, source_config: sourceConfig(), source_credential_id: sourceType === "rest" ? sourceCredential : null,
      destination_type: destinationType, destination_config: destinationConfig(), destination_credential_id: destinationCredential,
      mapping: mapping.filter((r) => r.source && r.target), schedule: sourceType === "webhook" ? "manual" : schedule, enabled,
    };
    try {
      const saved = initial ? await api.saveIntegration(initial.id, body) : await api.createIntegration(body);
      toast.success(initial ? "Integration saved" : "Integration created");
      router.push(`/app/integrations/${saved.id}`);
    } catch (err) {
      toast.error("Couldn't save", { description: (err as Error).message });
      setSaving(false);
    }
  }

  return (
    <form onSubmit={save} className="space-y-5">
      <Panel title="Basics" action={!initial ? <Button type="button" variant="outline" size="sm" onClick={useDemo}><FlaskConical />Use demo APIs</Button> : undefined} bodyClassName="grid grid-cols-1 gap-4 p-5 md:grid-cols-2">
        <div className="space-y-2"><Label htmlFor="i-name">Name</Label><Input id="i-name" required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} placeholder="CRM contacts → Mailing list" /></div>
        <div className="space-y-2"><Label htmlFor="i-desc">Description <span className="font-normal text-muted-foreground">(optional)</span></Label><Input id="i-desc" maxLength={500} value={description} onChange={(e) => setDescription(e.target.value)} /></div>
      </Panel>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Panel title="1 · Source" description="Where records come from." action={<TypeToggle value={sourceType} onChange={setSourceType} label="Source type" />} bodyClassName="space-y-4 p-5">
          {sourceType === "rest" ? (
            <>
              <div className="grid grid-cols-[100px_minmax(0,1fr)] gap-2">
                <Select value={sourceMethod} onValueChange={setSourceMethod}>
                  <SelectTrigger aria-label="Method" className="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="GET">GET</SelectItem><SelectItem value="POST">POST</SelectItem></SelectContent>
                </Select>
                <Input required type="url" value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)} placeholder="https://api.example.com/customers" className="font-mono text-[13px]" aria-label="Source URL" />
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="s-path">Records path</Label>
                  <Input id="s-path" value={recordsPath} onChange={(e) => setRecordsPath(e.target.value)} placeholder="data  (empty = top-level list)" className="font-mono text-[13px]" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="s-cred">Authentication</Label>
                  <CredentialSelect id="s-cred" value={sourceCredential} onChange={setSourceCredential} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="s-pages">Pagination</Label>
                  <Select value={pagination} onValueChange={setPagination}>
                    <SelectTrigger id="s-pages" className="w-full"><SelectValue /></SelectTrigger>
                    <SelectContent><SelectItem value="none">One request</SelectItem><SelectItem value="page">Page number (?page=1,2…)</SelectItem></SelectContent>
                  </Select>
                </div>
                {pagination === "page" ? (
                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-2"><Label htmlFor="s-param">Page param</Label><Input id="s-param" value={pageParam} onChange={(e) => setPageParam(e.target.value)} className="font-mono text-[13px]" /></div>
                    <div className="space-y-2"><Label htmlFor="s-max">Max pages</Label><Input id="s-max" type="number" min={1} max={50} value={maxPages} onChange={(e) => setMaxPages(Number(e.target.value))} /></div>
                  </div>
                ) : null}
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="space-y-2"><Label htmlFor="s-params">Query parameters</Label><Textarea id="s-params" rows={3} value={params} onChange={(e) => setParams(e.target.value)} placeholder="status=active" className="font-mono text-[12.5px]" /></div>
                <div className="space-y-2"><Label htmlFor="s-headers">Headers</Label><Textarea id="s-headers" rows={3} value={sourceHeaders} onChange={(e) => setSourceHeaders(e.target.value)} placeholder="Accept: application/json" className="font-mono text-[12.5px]" /></div>
              </div>
              <p className="text-xs text-muted-foreground">Tokens and API keys go in a <Link href="/app/credentials" className="text-primary hover:underline">stored credential</Link>, never in headers.</p>
            </>
          ) : (
            <>
              <p className="rounded-lg bg-accent px-3.5 py-3 text-sm text-accent-foreground">
                DataBridge generates a private URL after you save. Any app that POSTs JSON to it starts a run: one object, a list, or an object with a list inside.
              </p>
              <div className="space-y-2"><Label htmlFor="w-path">Records path</Label><Input id="w-path" value={recordsPath} onChange={(e) => setRecordsPath(e.target.value)} placeholder="empty = the body itself" className="font-mono text-[13px]" /></div>
            </>
          )}
          <Button type="button" variant="outline" size="sm" onClick={() => test("source")} disabled={testing !== null || (sourceType === "rest" && !sourceUrl)}>
            {testing === "source" ? <Loader2 className="animate-spin" /> : <PlugZap />}Test source
          </Button>
          <TestBadge result={sourceTest} />
        </Panel>

        <Panel title="3 · Destination" description="Where mapped records are sent." action={<TypeToggle value={destinationType} onChange={setDestinationType} label="Destination type" />} bodyClassName="space-y-4 p-5">
          <div className={cn("grid gap-2", destinationType === "rest" ? "grid-cols-[100px_minmax(0,1fr)]" : "grid-cols-1")}>
            {destinationType === "rest" ? (
              <Select value={destinationMethod} onValueChange={setDestinationMethod}>
                <SelectTrigger aria-label="Method" className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>{["POST", "PUT", "PATCH"].map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
              </Select>
            ) : null}
            <Input required value={destinationUrl} onChange={(e) => setDestinationUrl(e.target.value)} placeholder={destinationType === "rest" ? "https://api.example.com/contacts/{external_id}" : "https://hooks.example.com/incoming"} className="font-mono text-[13px]" aria-label="Destination URL" />
          </div>
          {destinationType === "rest" ? <p className="-mt-2 text-xs text-muted-foreground">Use <code className="font-mono">{"{field}"}</code> in the URL to insert a mapped value, e.g. for PUT updates.</p> : null}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="d-cred">{destinationType === "webhook" ? "Signing secret" : "Authentication"}</Label>
              <CredentialSelect id="d-cred" value={destinationCredential} onChange={setDestinationCredential} />
              {destinationType === "webhook" ? <p className="text-xs text-muted-foreground">Signs each delivery (X-DataBridge-Signature). The secret itself is never sent.</p> : null}
            </div>
            <div className="space-y-2"><Label htmlFor="d-headers">Headers</Label><Textarea id="d-headers" rows={3} value={destinationHeaders} onChange={(e) => setDestinationHeaders(e.target.value)} placeholder="X-Source: databridge" className="font-mono text-[12.5px]" /></div>
          </div>
          <Button type="button" variant="outline" size="sm" onClick={() => test("destination")} disabled={testing !== null || !destinationUrl}>
            {testing === "destination" ? <Loader2 className="animate-spin" /> : <PlugZap />}Test destination
          </Button>
          <TestBadge result={destinationTest} />
        </Panel>
      </div>

      <Panel title="2 · Field mapping" description="Pick the fields to send, rename them, and convert values. Test the source to load a real sample record." bodyClassName="p-5">
        <MappingEditor rules={mapping} onChange={setMapping} sample={sample} meta={meta.data} />
      </Panel>

      <Panel title="4 · Schedule" bodyClassName="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="inline-flex flex-wrap rounded-lg border bg-muted/60 p-0.5" role="radiogroup" aria-label="Schedule">
          {(meta.data?.schedules ?? []).map((s) => (
            <button key={s.value} type="button" role="radio" aria-checked={schedule === s.value} disabled={sourceType === "webhook" && s.value !== "manual"}
              onClick={() => setSchedule(s.value)}
              className={cn("rounded-md px-3 py-1.5 text-sm disabled:opacity-40", schedule === s.value ? "bg-card font-medium shadow-sm" : "text-muted-foreground hover:text-foreground")}>
              {s.label}
            </button>
          ))}
        </div>
        {sourceType === "webhook" ? <p className="text-xs text-muted-foreground">Webhook sources run whenever a webhook arrives.</p> : null}
        <label className="flex items-center gap-2 text-sm">
          <Switch checked={enabled} onCheckedChange={setEnabled} />Enabled
        </label>
      </Panel>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={() => router.back()}>Cancel</Button>
        <Button type="submit" disabled={saving}>{saving ? <Loader2 className="animate-spin" /> : null}{initial ? "Save integration" : "Create integration"}</Button>
      </div>
    </form>
  );
}
