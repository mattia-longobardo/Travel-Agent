"use client";

import { Building2, House, Hotel, Package, Plane } from "lucide-react";
import type { AccommodationType, SearchMode } from "@/lib/types";

const MODES: Array<{
  value: SearchMode;
  label: string;
  description: string;
  icon: typeof Plane;
}> = [
  { value: "hotel_only", label: "Solo hotel", description: "Alloggi senza volo", icon: Building2 },
  { value: "flight_only", label: "Solo volo", description: "Andata e ritorno", icon: Plane },
  { value: "flight_hotel", label: "Volo + hotel", description: "Confronta il viaggio completo", icon: Package },
];

const ACCOMMODATIONS: Array<{
  value: AccommodationType;
  label: string;
  description: string;
  icon: typeof Hotel;
}> = [
  { value: "hotel", label: "Hotel", description: "Hotel e resort", icon: Hotel },
  { value: "home", label: "Case", description: "Appartamenti e ville", icon: House },
  { value: "both", label: "Hotel e case", description: "Mostra entrambe", icon: Building2 },
];

export function TravelModeSelector({
  mode,
  accommodationType,
  onModeChange,
  onAccommodationTypeChange,
}: {
  mode: SearchMode;
  accommodationType: AccommodationType;
  onModeChange: (mode: SearchMode) => void;
  onAccommodationTypeChange: (type: AccommodationType) => void;
}) {
  return (
    <div className="flex w-full flex-col gap-4">
      <div>
        <p className="mb-2 text-left text-sm font-semibold">Cosa vuoi cercare?</p>
        <div
          role="tablist"
          aria-label="Tipo di ricerca"
          className="grid grid-cols-3 gap-2 rounded-xl bg-muted/80 p-1.5"
        >
          {MODES.map(({ value, label, description, icon: Icon }) => {
            const active = mode === value;
            return (
              <button
                key={value}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => onModeChange(value)}
                className={
                  "flex min-h-20 min-w-0 flex-col items-center justify-center gap-1 rounded-lg px-2 py-2 text-center transition " +
                  (active
                    ? "bg-background text-primary shadow-sm ring-1 ring-primary/20"
                    : "text-muted-foreground hover:bg-background/70 hover:text-foreground")
                }
              >
                <Icon aria-hidden="true" className="size-5 shrink-0" />
                <span className="text-xs font-semibold sm:text-sm">{label}</span>
                <span className="hidden text-[11px] leading-tight text-muted-foreground sm:block">
                  {description}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {mode !== "flight_only" && (
        <fieldset className="rounded-xl border bg-card p-3 text-left">
          <legend className="px-1 text-sm font-semibold">Tipo di alloggio</legend>
          <div role="radiogroup" aria-label="Tipo di alloggio" className="mt-1 grid grid-cols-3 gap-2">
            {ACCOMMODATIONS.map(({ value, label, description, icon: Icon }) => {
              const active = accommodationType === value;
              return (
                <button
                  key={value}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() => onAccommodationTypeChange(value)}
                  className={
                    "flex min-h-16 min-w-0 flex-col items-center justify-center gap-1 rounded-lg border px-2 py-2 text-center transition " +
                    (active
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border bg-background text-muted-foreground hover:border-primary/40")
                  }
                >
                  <Icon aria-hidden="true" className="size-4" />
                  <span className="text-xs font-semibold sm:text-sm">{label}</span>
                  <span className="hidden text-[10px] leading-tight text-muted-foreground sm:block">
                    {description}
                  </span>
                </button>
              );
            })}
          </div>
        </fieldset>
      )}
    </div>
  );
}
