"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Asterisk, GripVertical, Plus, Trash2 } from "lucide-react";
import { CodeBlock } from "@/components/app/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { api } from "@/lib/api";
import type { MappingRule, Meta } from "@/lib/types";
import { cn } from "@/lib/utils";

export const EMPTY_RULE: MappingRule = { source: "", target: "", transform: "none", argument: null, required: false, default: null };

/** Every dotted path in a sample record, for the source-field suggestions. */
export function fieldPaths(value: unknown, prefix = "", depth = 0): string[] {
  if (depth > 3 || value === null || typeof value !== "object") return prefix ? [prefix] : [];
  if (Array.isArray(value)) return value.length ? fieldPaths(value[0], prefix ? `${prefix}.0` : "0", depth + 1) : prefix ? [prefix] : [];
  return Object.entries(value as Record<string, unknown>).flatMap(([key, v]) => fieldPaths(v, prefix ? `${prefix}.${key}` : key, depth + 1));
}

export function MappingEditor({
  rules,
  onChange,
  sample,
  meta,
}: {
  rules: MappingRule[];
  onChange: (rules: MappingRule[]) => void;
  sample: Record<string, unknown> | null;
  meta: Meta | null;
}) {
  const [sampleText, setSampleText] = useState(() => JSON.stringify(sample ?? {}, null, 2));
  const [seenSample, setSeenSample] = useState(sample);
  if (sample !== seenSample) {
    setSeenSample(sample);
    setSampleText(JSON.stringify(sample ?? {}, null, 2));
  }
  const parsed = useMemo(() => {
    try {
      const value = JSON.parse(sampleText);
      return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
    } catch {
      return null;
    }
  }, [sampleText]);
  const fields = useMemo(() => (parsed ? fieldPaths(parsed) : []), [parsed]);
  const [preview, setPreview] = useState<{ ok: boolean; output: Record<string, unknown> | null; error: string | null } | null>(null);

  const complete = rules.filter((r) => r.source && r.target);
  const key = JSON.stringify([complete, parsed]);
  useEffect(() => {
    if (!parsed || !complete.length) return;
    const timer = setTimeout(() => {
      api.previewMapping(parsed, complete).then(setPreview).catch((err: Error) => setPreview({ ok: false, output: null, error: err.message }));
    }, 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const update = (index: number, patch: Partial<MappingRule>) => onChange(rules.map((r, i) => (i === index ? { ...r, ...patch } : r)));
  const transforms = meta?.transforms ?? [{ name: "none", label: "No change", needs_argument: false, argument_label: null }];

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
      <div>
        <div className="hidden grid-cols-[16px_minmax(0,1fr)_16px_minmax(0,0.9fr)_16px_minmax(0,1fr)_64px] items-center gap-2 px-1 pb-2 text-xs font-medium text-muted-foreground md:grid">
          <span /><span>Source field</span><span /><span>Transform</span><span /><span>Destination field</span><span />
        </div>
        <datalist id="source-fields">{fields.map((f) => <option key={f} value={f} />)}</datalist>
        <ol className="space-y-2">
          {rules.map((rule, index) => {
            const transform = transforms.find((t) => t.name === rule.transform);
            return (
              <li key={index} className="grid grid-cols-1 items-center gap-2 rounded-lg border bg-card p-2.5 md:grid-cols-[16px_minmax(0,1fr)_16px_minmax(0,0.9fr)_16px_minmax(0,1fr)_64px] md:border-0 md:bg-transparent md:p-0">
                <GripVertical className="hidden size-4 text-muted-foreground/50 md:block" aria-hidden />
                <Input list="source-fields" value={rule.source} onChange={(e) => update(index, { source: e.target.value })} placeholder="first_name" className="font-mono text-[13px]" aria-label={`Source field ${index + 1}`} />
                <ArrowRight className="hidden size-4 text-muted-foreground md:block" aria-hidden />
                <div className="flex gap-1.5">
                  <Select value={rule.transform} onValueChange={(value) => update(index, { transform: value, argument: transforms.find((t) => t.name === value)?.needs_argument ? rule.argument : null })}>
                    <SelectTrigger className="w-full min-w-0" aria-label={`Transform ${index + 1}`}><SelectValue /></SelectTrigger>
                    <SelectContent>{transforms.map((t) => <SelectItem key={t.name} value={t.name}>{t.label}</SelectItem>)}</SelectContent>
                  </Select>
                  {transform?.needs_argument ? (
                    <Input value={rule.argument ?? ""} onChange={(e) => update(index, { argument: e.target.value || null })} placeholder={transform.argument_label ?? ""} className="w-24 font-mono text-[13px]" aria-label={transform.argument_label ?? "Argument"} />
                  ) : null}
                </div>
                <ArrowRight className="hidden size-4 text-muted-foreground md:block" aria-hidden />
                <Input value={rule.target} onChange={(e) => update(index, { target: e.target.value })} placeholder="name" className="font-mono text-[13px]" aria-label={`Destination field ${index + 1}`} />
                <div className="flex justify-end gap-1">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button type="button" variant={rule.required ? "secondary" : "ghost"} size="icon-sm" aria-pressed={rule.required} aria-label="Required"
                        onClick={() => update(index, { required: !rule.required })} className={cn(rule.required && "text-primary")}>
                        <Asterisk />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>{rule.required ? "Required — records without it fail" : "Optional — skipped when missing"}</TooltipContent>
                  </Tooltip>
                  <Button type="button" variant="ghost" size="icon-sm" aria-label="Remove field" onClick={() => onChange(rules.filter((_, i) => i !== index))}><Trash2 /></Button>
                </div>
              </li>
            );
          })}
        </ol>
        <Button type="button" variant="outline" size="sm" className="mt-3" onClick={() => onChange([...rules, { ...EMPTY_RULE }])}><Plus />Add field</Button>
        {fields.length ? (
          <div className="mt-4">
            <p className="mb-1.5 text-xs text-muted-foreground">Fields in the sample — click to map one</p>
            <div className="flex flex-wrap gap-1.5">
              {fields.filter((f) => !rules.some((r) => r.source === f)).slice(0, 24).map((f) => (
                <button key={f} type="button" onClick={() => {
                  const rule = { ...EMPTY_RULE, source: f, target: f.split(".").pop() ?? f };
                  const blank = rules.findIndex((r) => !r.source && !r.target);
                  onChange(blank >= 0 ? rules.map((r, i) => (i === blank ? rule : r)) : [...rules, rule]);
                }}
                  className="rounded-md border bg-card px-2 py-0.5 font-mono text-[11.5px] text-muted-foreground hover:border-primary hover:text-primary">
                  + {f}
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </div>

      <div className="space-y-3">
        <div>
          <p className="mb-1.5 text-xs font-medium text-muted-foreground">Sample source record</p>
          <Textarea value={sampleText} onChange={(e) => setSampleText(e.target.value)} spellCheck={false} rows={9}
            className={cn("bg-code font-mono text-[12px] text-code-foreground", parsed === null && "border-destructive")} aria-label="Sample source record" />
          {parsed === null ? <p className="mt-1 text-xs text-destructive">Not a JSON object</p> : null}
        </div>
        <div>
          <p className="mb-1.5 text-xs font-medium text-muted-foreground">What the destination receives</p>
          {!complete.length ? (
            <p className="rounded-lg border border-dashed p-4 text-center text-xs text-muted-foreground">Add a field to see the output</p>
          ) : preview?.ok ? (
            <CodeBlock value={preview.output} />
          ) : preview ? (
            <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 font-mono text-xs text-destructive">{preview.error}</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
