"use client";
import type { AnalyticsPath } from "@/lib/types";

// Per-position token colors (cycled). Uses the theme `--chart-*` tokens so the chips
// stay legible in light and dark mode without any external chart dependency.
const CHIP_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
];

/** Renders an agent node-path as a row of colored chips joined by arrows. */
export function PathChips({ path }: { path: string[] }) {
  if (!path.length) {
    return <span className="text-sm text-muted-foreground">—</span>;
  }
  return (
    <span className="flex flex-wrap items-center gap-1">
      {path.map((node, i) => (
        <span key={`${node}-${i}`} className="flex items-center gap-1">
          {i > 0 && <span aria-hidden className="text-muted-foreground">→</span>}
          <span
            className="rounded-full px-2 py-0.5 text-xs font-medium"
            style={{ color: CHIP_COLORS[i % CHIP_COLORS.length], backgroundColor: "color-mix(in oklch, " + CHIP_COLORS[i % CHIP_COLORS.length] + " 14%, transparent)" }}
          >
            {node}
          </span>
        </span>
      ))}
    </span>
  );
}

function fmtMs(ms: number): string {
  if (!ms) return "0 ms";
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)} ms`;
}

export function AnalyticsPathGraph({ paths }: { paths: AnalyticsPath[] }) {
  const sorted = [...paths].sort((a, b) => b.count - a.count);
  const max = sorted.reduce((m, p) => Math.max(m, p.count), 0) || 1;

  if (!sorted.length) {
    return <p className="text-sm text-muted-foreground">Nessun percorso registrato.</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      {sorted.map((p, idx) => {
        const pct = Math.max(4, Math.round((p.count / max) * 100));
        return (
          <div key={idx} className="flex flex-col gap-1.5" data-testid="path-row">
            <div className="flex items-center justify-between gap-3">
              <PathChips path={p.path} />
              <div className="shrink-0 text-right text-xs text-muted-foreground">
                <span className="font-semibold text-foreground">{p.count}</span> run · {fmtMs(p.avg_latency_ms)} · {Math.round(p.avg_tokens)} tok
              </div>
            </div>
            <div className="h-2 w-full overflow-hidden rounded bg-muted">
              <div className="h-2 rounded bg-primary" style={{ width: `${pct}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
