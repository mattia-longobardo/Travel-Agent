"use client";
import { use, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertCircle, ArrowLeft, RefreshCw } from "lucide-react";
import { me, adminChatDetail } from "@/lib/api";
import type { AnalyticsChatDetail } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { MessageBubble } from "@/components/MessageBubble";
import { PathChips } from "@/components/AnalyticsPathGraph";

function fmtLatency(ms: number): string {
  if (!ms) return "0 ms";
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)} ms`;
}
function fmtNum(n: number): string {
  return (n ?? 0).toLocaleString("it-IT");
}
function fmtUsd(n: number): string {
  return `$${n.toFixed(n < 0.01 ? 4 : 2)}`;
}
function fmtCost(n: number | null): string {
  return n == null ? "n/d" : fmtUsd(n);
}
function fmtDate(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("it-IT", { dateStyle: "short", timeStyle: "short" });
}

type TabKey = "transcript" | "stats";
const RANGE_LABELS: Record<string, string> = {
  "7d": "ultimi 7 giorni",
  "30d": "ultimi 30 giorni",
  "90d": "ultimi 90 giorni",
  all: "intera durata della chat",
};

function Kpi({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-1 py-4">
        <span className="text-sm text-muted-foreground">{label}</span>
        <span className="text-2xl font-semibold">{value}</span>
        {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
      </CardContent>
    </Card>
  );
}

export default function AdminChatDetail({ params }: { params: Promise<{ id: string }> }) {
  // Next.js 16: route params are a Promise; unwrap with React `use()` in client components.
  const { id } = use(params);
  const chatId = Number(id);
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestedRange = searchParams.get("range") ?? "30d";
  const range = requestedRange in RANGE_LABELS ? requestedRange : "30d";
  const [data, setData] = useState<AnalyticsChatDetail | null>(null);
  const [tab, setTab] = useState<TabKey>("transcript");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDetail = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const u = await me();
      if (!u || !u.is_admin) { router.replace("/"); return; }
      setData(await adminChatDetail(chatId, range));
    } catch {
      setError("Non è stato possibile caricare il dettaglio della chat.");
    } finally {
      setLoading(false);
    }
  }, [router, chatId, range]);

  useEffect(() => {
    const timeout = window.setTimeout(() => { void loadDetail(); }, 0);
    return () => window.clearTimeout(timeout);
  }, [loadDetail]);

  const tabClass = (active: boolean) =>
    "rounded-md px-3 py-1.5 text-sm font-medium transition " +
    (active ? "bg-primary/10 text-primary shadow-sm" : "text-muted-foreground hover:bg-accent");

  return (
    <main className="travel-map-pattern min-h-screen">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6 md:py-10">
        <div className="flex items-center gap-3">
          <Button type="button" variant="outline" size="icon" aria-label="Indietro" onClick={() => router.back()}>
            <ArrowLeft aria-hidden="true" />
          </Button>
          <div className="min-w-0">
            <h1 className="truncate text-2xl font-semibold">{data?.chat.title ?? "Chat"}</h1>
            <p className="text-sm text-muted-foreground">
              {data ? `Proprietario: ${data.chat.owner_username} · Chat creata: ${fmtDate(data.chat.created_at)}` : "Caricamento…"}
            </p>
            <p className="text-xs text-muted-foreground">
              Messaggi, run e metriche: {RANGE_LABELS[data?.range ?? range]}.
            </p>
          </div>
        </div>

        <div className="flex w-fit gap-1 rounded-lg bg-muted p-1">
          <button type="button" className={tabClass(tab === "transcript")} onClick={() => setTab("transcript")}>
            Transcript
          </button>
          <button type="button" className={tabClass(tab === "stats")} onClick={() => setTab("stats")}>
            Statistiche
          </button>
        </div>

        {error && (
          <div role="alert" className="flex flex-wrap items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm">
            <AlertCircle aria-hidden className="size-4 text-destructive" />
            <span className="min-w-0 flex-1">{error}</span>
            <Button type="button" variant="outline" size="sm" className="gap-2" onClick={() => void loadDetail()}>
              <RefreshCw aria-hidden className="size-3.5" /> Riprova
            </Button>
          </div>
        )}

        {tab === "transcript" && (
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
            {loading && <p className="text-center text-sm text-muted-foreground">Caricamento…</p>}
            {data?.messages.map((m, i) => (
              <div key={i} className="flex flex-col gap-1">
                <MessageBubble role={m.role} content={m.content} createdAt={m.created_at} />
                {m.tool_calls != null && (
                  <details className="mx-auto w-full max-w-3xl rounded-md border bg-muted/30 px-3 py-2 text-xs">
                    <summary className="cursor-pointer text-muted-foreground">Tool calls</summary>
                    <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words">{JSON.stringify(m.tool_calls, null, 2)}</pre>
                  </details>
                )}
              </div>
            ))}
            {data && data.messages.length === 0 && (
              <p className="text-center text-sm text-muted-foreground">Nessun messaggio.</p>
            )}
          </div>
        )}

        {tab === "stats" && data && (
          <div className="flex flex-col gap-6">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Kpi label="Messaggi" value={fmtNum(data.stats.message_count)} />
              <Kpi label="Run" value={fmtNum(data.stats.run_count)} />
              <Kpi
                label="Successo"
                value={`${(data.stats.success_rate * 100).toFixed(1)}%`}
                sub={`${data.stats.success_count} ok · ${data.stats.error_count} errori · ${data.stats.cancelled_count} annullati`}
              />
              <Kpi label="Token totali" value={fmtNum(data.stats.total_tokens)} />
              <Kpi label="Latenza media" value={fmtLatency(data.stats.avg_latency_ms)} />
              <Kpi label="Token input" value={fmtNum(data.stats.prompt_tokens)} />
              <Kpi label="Token output" value={fmtNum(data.stats.completion_tokens)} />
              <Kpi
                label="Costo stimato"
                value={data.stats.has_unpriced && data.stats.estimated_cost_usd === 0 ? "n/d" : fmtUsd(data.stats.estimated_cost_usd)}
                sub={data.stats.has_unpriced ? "Totale parziale: modelli senza tariffa esclusi" : undefined}
              />
            </div>

            <Card>
              <CardContent className="overflow-x-auto py-4">
                <table className="w-full min-w-[640px] text-sm">
                  <thead>
                    <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
                      <th className="py-2 pr-3 font-medium">Quando</th>
                      <th className="py-2 pr-3 font-medium">Percorso</th>
                      <th className="py-2 pr-3 text-right font-medium">Token</th>
                      <th className="py-2 pr-3 text-right font-medium">Latenza</th>
                      <th className="py-2 pr-3 text-right font-medium">Costo</th>
                      <th className="py-2 pr-3 font-medium">Modello</th>
                      <th className="py-2 pr-3 font-medium">Esito</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.runs.map((r, i) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="py-2 pr-3 whitespace-nowrap text-muted-foreground">{fmtDate(r.created_at)}</td>
                        <td className="py-2 pr-3"><PathChips path={r.node_path} /></td>
                        <td className="py-2 pr-3 text-right">{fmtNum(r.total_tokens)}</td>
                        <td className="py-2 pr-3 text-right whitespace-nowrap">{fmtLatency(r.latency_ms)}</td>
                        <td className="py-2 pr-3 text-right whitespace-nowrap">{fmtCost(r.cost_usd)}</td>
                        <td className="py-2 pr-3 whitespace-nowrap text-muted-foreground">{r.model ?? "—"}</td>
                        <td className="py-2 pr-3">
                          <Badge variant={r.outcome === "success" ? "secondary" : r.outcome === "error" ? "destructive" : "outline"}>
                            {r.outcome === "success" ? "OK" : r.outcome === "error" ? "Errore" : "Annullato"}
                          </Badge>
                          {r.outcome === "error" && r.error && (
                            <div className="mt-1 max-w-[22rem] font-mono text-xs text-destructive break-words">{r.error}</div>
                          )}
                        </td>
                      </tr>
                    ))}
                    {data.runs.length === 0 && (
                      <tr><td colSpan={7} className="py-6 text-center text-sm text-muted-foreground">Nessun run.</td></tr>
                    )}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </main>
  );
}
