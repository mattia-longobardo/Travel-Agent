import { Building2, CalendarDays, MapPin, Plane, Sparkles, Users, WalletCards } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { BriefData } from "@/lib/types";

function rows(brief: BriefData | null) {
  const out: { icon: typeof MapPin; label: string; value: string; hint?: string }[] = [];
  if (brief?.search_mode) {
    const mode = brief.search_mode === "flight_only"
      ? "Solo volo"
      : brief.search_mode === "hotel_only"
        ? "Solo alloggio"
        : "Volo + hotel";
    out.push({ icon: Building2, label: "Ricerca", value: mode });
  }
  if (brief?.search_mode !== "flight_only" && brief?.accommodation_type) {
    const accommodation = brief.accommodation_type === "home"
      ? "Case"
      : brief.accommodation_type === "hotel"
        ? "Hotel"
        : "Hotel e case";
    out.push({ icon: Building2, label: "Alloggio", value: accommodation });
  }
  if (brief?.search_mode !== "flight_only" && brief?.accommodation_area?.trim()) {
    out.push({ icon: MapPin, label: "Zona alloggio", value: brief.accommodation_area.trim() });
  }
  out.push({ icon: MapPin, label: "Destinazione", value: brief?.destination_hint || "Da definire" });
  if (brief?.dates_flexible && brief?.window_from) {
    const nights = brief.trip_nights ? ` · ${brief.trip_nights} notti` : "";
    out.push({ icon: CalendarDays, label: "Date",
      value: `${brief.window_from} – ${brief.window_to ?? brief.window_from}${nights}`,
      hint: "date flessibili — date esatte secondo l'offerta" });
  } else if (brief?.date_from) {
    out.push({ icon: CalendarDays, label: "Date",
      value: brief.date_to ? `${brief.date_from} → ${brief.date_to}` : brief.date_from });
  }
  if (brief?.origin_iata?.length) {
    out.push({ icon: Plane, label: "Partenza", value: brief.origin_iata[0] });
  }
  if (brief?.adults) {
    const kids = brief.children_ages?.length ? ` + ${brief.children_ages.length} bimbi` : "";
    out.push({ icon: Users, label: "Viaggiatori", value: `${brief.adults} adulti${kids}` });
  }
  // Defense-in-depth: only render a numeric budget. A malformed value (e.g. an unparsed
  // free-text answer that slipped through) is skipped instead of showing "NaN EUR".
  if (brief?.budget_per_person && Number.isFinite(Number(brief.budget_per_person))) {
    out.push({ icon: WalletCards, label: "Budget",
      value: `${Math.round(Number(brief.budget_per_person)).toLocaleString("it-IT")} ${brief.currency} a persona` });
  }
  if (brief?.min_stars) {
    out.push({ icon: Sparkles, label: "Hotel", value: `★${brief.min_stars}+` });
  }
  return out;
}

export function BriefPanel({ brief }: { brief: BriefData | null }) {
  return (
    <section className="rounded-lg border bg-card p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold">Brief viaggio</h2>
        <Badge variant="secondary">{brief ? "Aggiornato" : "Bozza"}</Badge>
      </div>
      <div className="flex flex-col gap-3">
        {rows(brief).map((item) => (
          <div key={item.label} className="grid grid-cols-[1.25rem_6rem_minmax(0,1fr)] gap-2 text-sm">
            <item.icon aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <span className="text-muted-foreground">{item.label}</span>
            <span className="min-w-0 text-right font-medium break-words">
              {item.value}
              {item.hint ? (
                <span className="mt-0.5 block text-xs font-normal text-muted-foreground break-words">{item.hint}</span>
              ) : null}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
