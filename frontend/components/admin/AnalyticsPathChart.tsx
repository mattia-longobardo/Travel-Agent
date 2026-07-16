"use client";
import type { AnalyticsPath } from "@/lib/types";
import { AnalyticsPathGraph } from "@/components/AnalyticsPathGraph";

export function AnalyticsPathChart({ paths }: { paths: AnalyticsPath[] }) {
  if (!paths.length) return <p className="py-10 text-center text-sm text-muted-foreground">Nessun percorso.</p>;
  return <AnalyticsPathGraph paths={paths.slice(0, 12)} />;
}
