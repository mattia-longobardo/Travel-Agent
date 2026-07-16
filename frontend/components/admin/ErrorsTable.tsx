"use client";
import Link from "next/link";
import type { AnalyticsErrorRow } from "@/lib/types";

const fmtDate = (iso?: string | null) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleString("it-IT", { dateStyle: "short", timeStyle: "short" });
};

export function ErrorsTable({ items, range }: { items: AnalyticsErrorRow[]; range: string }) {
  if (!items.length) return <p className="py-10 text-center text-sm text-muted-foreground">Nessun errore nel periodo.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] text-sm">
        <thead>
          <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
            <th className="py-2 pr-3 font-medium">Quando</th>
            <th className="py-2 pr-3 font-medium">Chat</th>
            <th className="py-2 pr-3 font-medium">Proprietario</th>
            <th className="py-2 pr-3 font-medium">Modello</th>
            <th className="py-2 pr-3 font-medium">Errore</th>
          </tr>
        </thead>
        <tbody>
          {items.map((e, i) => (
            <tr key={i} className="border-b align-top last:border-0">
              <td className="py-2 pr-3 whitespace-nowrap text-muted-foreground">{fmtDate(e.created_at)}</td>
              <td className="py-2 pr-3">
                <Link href={`/admin/analytics/chats/${e.chat_id}?range=${encodeURIComponent(range)}`} className="text-primary hover:underline">{e.chat_title}</Link>
              </td>
              <td className="py-2 pr-3">{e.owner_username}</td>
              <td className="py-2 pr-3 whitespace-nowrap text-muted-foreground">{e.model ?? "—"}</td>
              <td className="py-2 pr-3 font-mono text-xs text-destructive break-words">{e.error ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
