"use client";
import type { ModelsResult } from "@/lib/types";

const fmt = (n: number) => (n ?? 0).toLocaleString("it-IT");
const usd = (n: number | null) => (n == null ? "n/d" : `$${n.toFixed(n < 0.01 ? 4 : 2)}`);

export function ModelBreakdownTable({ data }: { data: ModelsResult }) {
  if (!data.items.length) return <p className="py-6 text-center text-sm text-muted-foreground">Nessun dato.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] text-sm">
        <thead>
          <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
            <th className="py-2 pr-3 font-medium">Modello</th>
            <th className="py-2 pr-3 text-right font-medium">Run</th>
            <th className="py-2 pr-3 text-right font-medium">Token in</th>
            <th className="py-2 pr-3 text-right font-medium">Token out</th>
            <th className="py-2 pr-3 text-right font-medium">Latenza</th>
            <th className="py-2 pr-3 text-right font-medium">Successo</th>
            <th className="py-2 pr-3 text-right font-medium">Costo/run</th>
            <th className="py-2 pr-3 text-right font-medium">Costo</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((m) => (
            <tr key={m.model ?? "—"} className="border-b last:border-0">
              <td className="py-2 pr-3 font-medium">{m.model ?? "—"}</td>
              <td className="py-2 pr-3 text-right">{fmt(m.runs)}</td>
              <td className="py-2 pr-3 text-right">{fmt(m.prompt_tokens)}</td>
              <td className="py-2 pr-3 text-right">{fmt(m.completion_tokens)}</td>
              <td className="py-2 pr-3 text-right">{m.avg_latency_ms} ms</td>
              <td className="py-2 pr-3 text-right">
                <span className="font-medium">{(m.success_rate * 100).toFixed(1)}%</span>
                <span className="block text-xs text-muted-foreground">
                  {fmt(m.successes)} ok · {fmt(m.errors)} err · {fmt(m.cancelled)} ann.
                </span>
              </td>
              <td className="py-2 pr-3 text-right">{usd(m.cost_per_run_usd)}</td>
              <td className="py-2 pr-3 text-right">{usd(m.cost_usd)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t font-medium">
            <td className="py-2 pr-3" colSpan={7}>Totale</td>
            <td className="py-2 pr-3 text-right">{usd(data.total_cost_usd)}</td>
          </tr>
        </tfoot>
      </table>
      {data.has_unpriced && (
        <p className="mt-2 text-xs text-muted-foreground">Stima in USD; alcuni modelli non hanno tariffa nota (n/d) e sono esclusi dal totale.</p>
      )}
    </div>
  );
}
