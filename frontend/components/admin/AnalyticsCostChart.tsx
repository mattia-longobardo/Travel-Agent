"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AnalyticsDay } from "@/lib/types";

const fmtUsd = (value: number) => `$${value.toFixed(value < 0.01 ? 6 : 2)}`;

function CostTooltip({ active, label, payload }: {
  active?: boolean;
  label?: string | number;
  payload?: ReadonlyArray<{ payload?: AnalyticsDay }>;
}) {
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;
  return (
    <div className="rounded-md border bg-background px-3 py-2 text-xs shadow-md">
      <p className="mb-1 font-medium">{String(label)}</p>
      <p>Costo: {fmtUsd(row.estimated_cost_usd)}{row.has_unpriced ? " (parziale)" : ""}</p>
      <p>Token: {row.tokens.toLocaleString("it-IT")}</p>
    </div>
  );
}

export function AnalyticsCostChart({ data }: { data: AnalyticsDay[] }) {
  if (!data.length) return <p className="py-10 text-center text-sm text-muted-foreground">Nessun dato nel periodo.</p>;
  return (
    <div className="h-52 w-full" aria-label="Costo stimato per giorno">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis dataKey="day" tickFormatter={(d: string) => d.slice(5)} fontSize={11} />
          <YAxis width={54} tickFormatter={(v: number) => `$${v.toFixed(v < 0.01 ? 3 : 2)}`} fontSize={11} />
          <Tooltip content={<CostTooltip />} />
          <Bar dataKey="estimated_cost_usd" name="Costo stimato" fill="var(--chart-1)" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
