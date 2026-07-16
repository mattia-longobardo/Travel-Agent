"use client";

import type { ResultBatch } from "@/lib/types";

function batchKind(batch: ResultBatch): string {
  if (batch.packages.every((item) => item.kind === "flight_only")) return "Voli";
  if (batch.packages.every((item) => item.kind === "hotel_only")) return "Alloggi";
  return "Volo + hotel";
}

export function ResultBatchSelector({ batches, selectedId, onSelect, className = "" }: {
  batches: ResultBatch[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  className?: string;
}) {
  if (batches.length < 2) return null;

  return (
    <label className={`flex min-w-0 flex-col gap-1.5 ${className}`}>
      <span className="text-xs font-medium text-muted-foreground">Cronologia risultati</span>
      <select
        aria-label="Seleziona una ricerca precedente"
        value={selectedId ?? batches.at(-1)?.id ?? ""}
        onChange={(event) => onSelect(event.target.value)}
        className="min-h-10 w-full rounded-lg border bg-background px-3 text-sm font-medium outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
      >
        {batches.map((batch, index) => {
          const count = batch.packages.length;
          const newest = index === batches.length - 1 ? " · più recente" : "";
          return (
            <option key={batch.id} value={batch.id}>
              Ricerca {index + 1} · {batchKind(batch)} · {count} {count === 1 ? "opzione" : "opzioni"}{newest}
            </option>
          );
        })}
      </select>
    </label>
  );
}
