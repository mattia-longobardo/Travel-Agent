import { BarChart3 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { LocationSelector } from "@/components/LocationSelector";
import type { LocationGroup } from "@/lib/grouping";
import type { PackageCardData, SearchMode } from "@/lib/types";
import {
  AccommodationViewButton,
  accommodationLabel,
  accommodationWarnings,
} from "@/components/AccommodationViewButton";
import { ResultBatchSelector } from "@/components/ResultBatchSelector";
import type { ResultBatch } from "@/lib/types";

export function MiniResult({ item }: { item: PackageCardData }) {
  const price = Math.round(item.price_per_person).toLocaleString("it-IT");
  const remote = !!item.image_url && /^https?:\/\//.test(item.image_url);
  const accommodation = accommodationLabel(item);
  const warnings = accommodationWarnings(item);
  return (
    <article className="rounded-lg border bg-background p-2 transition hover:border-primary/40 hover:shadow-sm">
      <div className="grid grid-cols-[5rem_minmax(0,1fr)] gap-3">
      <div
        className="travel-destination-thumb min-h-20 rounded-md bg-cover bg-center"
        data-destination={remote ? undefined : item.badge || item.kind}
        style={remote ? { backgroundImage: `url(${item.image_url})` } : undefined}
      />
      <div className="min-w-0">
        {item.badge === "best_value" && (
          <Badge className="mb-1 bg-primary text-primary-foreground">Miglior valore</Badge>
        )}
        <div className="break-words text-sm font-semibold">{price} {item.currency}</div>
        <div className="break-words text-xs text-muted-foreground">
          a persona
          {item.kind === "flight_only" ? " · solo volo" : item.kind === "hotel_only" ? ` · solo ${accommodation.toLowerCase()}` : ""}
        </div>
        <div className="mt-1 break-words text-xs">
          {item.kind === "flight_only"
            ? item.flight_summary || "Solo volo"
            : `${item.hotel_stars ? `${"★".repeat(item.hotel_stars)} ` : ""}${item.hotel_name || (accommodation === "Casa" ? "Casa selezionata" : "Hotel selezionato")}`}
        </div>
        {warnings.length > 0 && (
          <div className="mt-1 break-words text-xs font-medium text-amber-700" title={warnings.join(" · ")}>
            ⚠ {warnings[0]}
          </div>
        )}
      </div>
      </div>
      {item.kind !== "flight_only" && (
        <div className="mt-2"><AccommodationViewButton data={item} compact /></div>
      )}
      {item.kind === "flight_only" && item.booking_url && (
        <a href={item.booking_url} target="_blank" rel="noopener noreferrer"
          className="mt-2 inline-flex min-h-10 w-full items-center justify-center rounded-lg bg-[var(--travel-coral)] px-2 text-xs font-semibold text-white">
          Prenota volo
        </a>
      )}
    </article>
  );
}

export function ResultsPanel({
  packages,
  groups,
  selectedLocation,
  onSelectLocation,
  searchMode,
  resultBatches,
  selectedResultBatchId,
  onSelectResultBatch,
}: {
  packages: PackageCardData[];
  groups: LocationGroup[];
  selectedLocation: string | null;
  onSelectLocation: (key: string) => void;
  searchMode?: SearchMode;
  resultBatches: ResultBatch[];
  selectedResultBatchId: string | null;
  onSelectResultBatch: (id: string) => void;
}) {
  const activeGroup = groups.find((g) => g.key === selectedLocation) ?? groups[0];
  const items = groups.length > 1 ? (activeGroup?.items ?? []) : packages;
  return (
    <section className="flex min-h-0 flex-1 flex-col rounded-lg border bg-card p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold">
          {searchMode === "flight_only" ? "Voli" : searchMode === "hotel_only" ? "Alloggi" : "Volo + hotel"}
        </h2>
        <span className="text-xs text-muted-foreground">{packages.length} opzioni</span>
      </div>
      <ResultBatchSelector
        batches={resultBatches}
        selectedId={selectedResultBatchId}
        onSelect={onSelectResultBatch}
        className="mb-3 shrink-0"
      />
      {groups.length > 1 && activeGroup && (
        <LocationSelector groups={groups} selected={activeGroup.key} onSelect={onSelectLocation} className="mb-3 shrink-0" />
      )}
      {items.length > 0 ? (
        <div className="flex min-h-0 flex-col gap-2 overflow-auto pr-1">
          {items.map((item) => (<MiniResult key={item.id} item={item} />))}
        </div>
      ) : (
        <div className="grid flex-1 place-items-center rounded-lg border border-dashed p-6 text-center">
          <div>
            <BarChart3 aria-hidden="true" className="mx-auto mb-2 text-muted-foreground" />
            <p className="text-sm font-medium">Nessun risultato ancora</p>
            <p className="mt-1 text-xs text-muted-foreground">I pacchetti compariranno qui durante la ricerca.</p>
          </div>
        </div>
      )}
    </section>
  );
}
