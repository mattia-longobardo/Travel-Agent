"use client";
import Link from "next/link";
import { ArrowDownUp, ExternalLink } from "lucide-react";
import type { AnalyticsChatRow } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

const fmtNum = (n: number) => (n ?? 0).toLocaleString("it-IT");
const fmtLat = (ms: number) => (!ms ? "0 ms" : ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)} ms`);
const fmtUsd = (n: number) => `$${n.toFixed(n < 0.01 ? 4 : 2)}`;
const fmtDate = (iso?: string | null) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleString("it-IT", { dateStyle: "short", timeStyle: "short" });
};

const SORTABLE_BEFORE_OUTCOME: { key: string; label: string; num?: boolean }[] = [
  { key: "created_at", label: "Creata" }, { key: "last_message_at", label: "Ultimo msg" },
  { key: "message_count", label: "Msg", num: true }, { key: "run_count", label: "Run", num: true },
];
const SORTABLE_AFTER_OUTCOME: { key: string; label: string; num?: boolean }[] = [
  { key: "total_tokens", label: "Token", num: true }, { key: "avg_latency_ms", label: "Latenza", num: true },
  { key: "estimated_cost_usd", label: "Costo", num: true },
];

function OutcomeCell({ row }: { row: AnalyticsChatRow }) {
  if (!row.run_count) return <Badge variant="outline">Nessun run</Badge>;
  const variant = row.error_count ? "destructive" : row.success_count ? "secondary" : "outline";
  const label = row.error_count ? "Con errori" : row.success_count ? "Completata" : "Annullata";
  return (
    <div className="flex min-w-28 flex-col items-end gap-1">
      <Badge variant={variant}>{label}</Badge>
      <span className="text-xs text-muted-foreground">
        {(row.success_rate * 100).toFixed(0)}% · {row.error_count} err · {row.cancelled_count} ann.
      </span>
    </div>
  );
}

export function ChatsAnalyticsTable({ rows, range, sort, order, onSort }: {
  rows: AnalyticsChatRow[]; range: string; sort: string; order: string; onSort: (c: string) => void;
}) {
  const arrow = (k: string) => (sort === k ? (order === "asc" ? " ↑" : " ↓") : "");
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[900px] text-sm">
        <thead>
          <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
            <th className="py-2 pr-3 font-medium">Proprietario</th>
            <th className="py-2 pr-3 font-medium">Titolo</th>
            {SORTABLE_BEFORE_OUTCOME.map((c) => (
              <th key={c.key} className={"py-2 pr-3 font-medium" + (c.num ? " text-right" : "")}>
                <button type="button" className="inline-flex items-center gap-1 hover:text-foreground" onClick={() => onSort(c.key)}>
                  <ArrowDownUp aria-hidden className="size-3" /> {c.label}{arrow(c.key)}
                </button>
              </th>
            ))}
            <th className="py-2 pr-3 text-right font-medium">Esito</th>
            {SORTABLE_AFTER_OUTCOME.map((c) => (
              <th key={c.key} className={"py-2 pr-3 font-medium" + (c.num ? " text-right" : "")}>
                <button type="button" className="inline-flex items-center gap-1 hover:text-foreground" onClick={() => onSort(c.key)}>
                  <ArrowDownUp aria-hidden className="size-3" /> {c.label}{arrow(c.key)}
                </button>
              </th>
            ))}
            <th className="py-2 pr-3 font-medium" />
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.chat_id} className="border-b last:border-0">
              <td className="py-2 pr-3">{r.owner_username}</td>
              <td className="py-2 pr-3 max-w-[16rem] truncate">{r.title}</td>
              <td className="py-2 pr-3 whitespace-nowrap text-muted-foreground">{fmtDate(r.created_at)}</td>
              <td className="py-2 pr-3 whitespace-nowrap text-muted-foreground">{fmtDate(r.last_message_at)}</td>
              <td className="py-2 pr-3 text-right">{fmtNum(r.message_count)}</td>
              <td className="py-2 pr-3 text-right">{fmtNum(r.run_count)}</td>
              <td className="py-2 pr-3"><OutcomeCell row={r} /></td>
              <td className="py-2 pr-3 text-right">{fmtNum(r.total_tokens)}</td>
              <td className="py-2 pr-3 text-right whitespace-nowrap">{fmtLat(r.avg_latency_ms)}</td>
              <td className="py-2 pr-3 text-right whitespace-nowrap">
                {r.has_unpriced && r.estimated_cost_usd === 0 ? "n/d" : fmtUsd(r.estimated_cost_usd)}
                {r.has_unpriced && r.estimated_cost_usd > 0 && <span className="ml-1 text-muted-foreground">parziale</span>}
              </td>
              <td className="py-2 pr-3">
                <Link href={`/admin/analytics/chats/${r.chat_id}?range=${encodeURIComponent(range)}`} className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-primary hover:bg-primary/10">
                  <ExternalLink aria-hidden className="size-3.5" /> Apri
                </Link>
              </td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr><td colSpan={11} className="py-6 text-center text-sm text-muted-foreground">Nessuna chat.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
