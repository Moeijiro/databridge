"use client";

import { useState } from "react";
import { KeyRound, Loader2, Plus, RotateCw, ShieldCheck, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Empty, ErrorState, PageTitle, Panel, RowsLoading } from "@/components/app/ui";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useApi } from "@/hooks/use-api";
import { api } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import type { AuthType, Credential } from "@/lib/types";

const TYPES: Record<AuthType, string> = { bearer: "Bearer token", api_key: "API key header", basic: "Basic auth" };

function CredentialDialog({ open, onOpenChange, existing, onSaved }: { open: boolean; onOpenChange: (o: boolean) => void; existing: Credential | null; onSaved: () => void }) {
  const [name, setName] = useState(existing?.name ?? "");
  const [type, setType] = useState<AuthType>(existing?.auth_type ?? "bearer");
  const [header, setHeader] = useState(existing?.header_name ?? "X-API-Key");
  const [username, setUsername] = useState(existing?.username ?? "");
  const [secret, setSecret] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{existing ? `Rotate “${existing.name}”` : "New credential"}</DialogTitle>
          <DialogDescription>Encrypted before it&apos;s stored. After saving, only the last four characters are ever shown.</DialogDescription>
        </DialogHeader>
        <form className="space-y-4" onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true);
          try {
            if (existing) await api.updateCredential(existing.id, { secret, name });
            else await api.createCredential({ name, auth_type: type, secret, header_name: type === "api_key" ? header : null, username: type === "basic" ? username : null });
            toast.success(existing ? "Secret rotated" : "Credential saved");
            onSaved();
            onOpenChange(false);
          } catch (err) {
            toast.error("Couldn't save", { description: (err as Error).message });
          } finally {
            setBusy(false);
          }
        }}>
          <div className="space-y-2"><Label htmlFor="c-name">Name</Label><Input id="c-name" required maxLength={80} value={name} onChange={(e) => setName(e.target.value)} placeholder="HubSpot production" /></div>
          {!existing ? (
            <div className="space-y-2">
              <Label htmlFor="c-type">Type</Label>
              <Select value={type} onValueChange={(v) => setType(v as AuthType)}>
                <SelectTrigger id="c-type" className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>{Object.entries(TYPES).map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          ) : null}
          {!existing && type === "api_key" ? <div className="space-y-2"><Label htmlFor="c-header">Header name</Label><Input id="c-header" required value={header} onChange={(e) => setHeader(e.target.value)} className="font-mono" /></div> : null}
          {!existing && type === "basic" ? <div className="space-y-2"><Label htmlFor="c-user">Username</Label><Input id="c-user" required value={username} onChange={(e) => setUsername(e.target.value)} /></div> : null}
          <div className="space-y-2">
            <Label htmlFor="c-secret">{type === "basic" ? "Password" : type === "api_key" ? "Key" : "Token"}</Label>
            <Input id="c-secret" required type="password" autoComplete="off" value={secret} onChange={(e) => setSecret(e.target.value)} className="font-mono" />
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={busy}>{busy ? <Loader2 className="animate-spin" /> : null}{existing ? "Rotate secret" : "Save credential"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function CredentialsPage() {
  const list = useApi(() => api.credentials(), "credentials");
  const [dialog, setDialog] = useState<{ open: boolean; existing: Credential | null }>({ open: false, existing: null });

  return (
    <>
      <PageTitle title="Credentials" description="API tokens, keys and passwords used by integrations. Stored encrypted; never shown again after saving."
        actions={<Button onClick={() => setDialog({ open: true, existing: null })}><Plus />New credential</Button>} />
      <Panel>
        {list.loading ? <RowsLoading /> : list.error ? <div className="p-5"><ErrorState message={list.error} /></div> : list.data?.length ? (
          <ul className="divide-y">
            {list.data.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center gap-4 px-5 py-3.5">
                <span className="flex size-9 items-center justify-center rounded-lg bg-accent"><KeyRound className="size-4 text-primary" /></span>
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{c.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {TYPES[c.auth_type]}{c.header_name ? ` · ${c.header_name}` : ""}{c.username ? ` · ${c.username}` : ""} · <span className="font-mono">{c.secret_hint}</span>
                  </p>
                </div>
                <p className="text-xs text-muted-foreground">Used by {c.used_by} · last used {timeAgo(c.last_used_at)}</p>
                <div className="flex gap-1">
                  <Button variant="ghost" size="sm" onClick={() => setDialog({ open: true, existing: c })}><RotateCw />Rotate</Button>
                  <Button variant="ghost" size="icon-sm" aria-label={`Delete ${c.name}`} onClick={async () => {
                    if (!window.confirm(c.used_by ? `“${c.name}” is used by ${c.used_by} integration(s); they'll run without auth. Delete?` : `Delete “${c.name}”?`)) return;
                    await api.deleteCredential(c.id);
                    list.reload();
                  }}><Trash2 /></Button>
                </div>
              </li>
            ))}
          </ul>
        ) : <Empty icon={ShieldCheck} title="No credentials yet" description="Add a token or API key, then pick it in an integration." />}
      </Panel>
      {dialog.open ? <CredentialDialog key={dialog.existing?.id ?? "new"} open={dialog.open} onOpenChange={(open) => setDialog((d) => ({ ...d, open }))} existing={dialog.existing} onSaved={list.reload} /> : null}
    </>
  );
}
