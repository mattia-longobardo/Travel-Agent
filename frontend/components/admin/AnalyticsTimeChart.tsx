"use client";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from "recharts";
import type { AnalyticsDay } from "@/lib/types";

export function AnalyticsTimeChart({ data }: { data: AnalyticsDay[] }) {
  if (!data.length) return <p className="py-10 text-center text-sm text-muted-foreground">Nessun dato nel periodo.</p>;
  return (
    <div className="h-64 w-full" aria-label="Esiti dei run per giorno">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis dataKey="day" tickFormatter={(d: string) => d.slice(5)} fontSize={11} />
          <YAxis allowDecimals={false} fontSize={11} />
          <Tooltip />
          <Legend />
          <Bar stackId="outcome" dataKey="successes" name="Riusciti" fill="var(--chart-2)" />
          <Bar stackId="outcome" dataKey="errors" name="Errori tecnici" fill="var(--destructive)" />
          <Bar stackId="outcome" dataKey="cancelled" name="Annullati" fill="var(--chart-4)" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
