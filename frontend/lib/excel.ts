import * as XLSX from "xlsx";
import type { PackageCardData } from "@/lib/types";

export const XLSX_HEADERS = [
  "Destinazione",
  "Partenza",
  "Prezzo/persona",
  "Prezzo totale",
  "Valuta",
  "Notti",
  "Dal",
  "Al",
  "Hotel",
  "Stelle",
  "Rating",
  "Volo",
  "Avvisi",
  "Link",
] as const;

/** Human-readable location label for a card. */
function locationOf(p: PackageCardData): string {
  return p.dest_name ?? p.destination ?? "";
}

/** Grouping key for "distinct location" detection: prefer the IATA code, fall back to the label. */
function locationKey(p: PackageCardData): string {
  return p.dest_iata ?? locationOf(p);
}

function rowFor(p: PackageCardData): Record<string, string | number> {
  return {
    Destinazione: p.destination ?? "",
    Partenza: p.departure_iata ?? "",
    "Prezzo/persona": Math.round(p.price_per_person),
    "Prezzo totale": Math.round(p.price_total),
    Valuta: p.currency ?? "",
    Notti: p.nights ?? 0,
    Dal: p.date_from ?? "",
    Al: p.date_to ?? "",
    Hotel: p.hotel_name ?? "",
    Stelle: p.hotel_stars ?? "",
    Rating: p.hotel_rating ?? "",
    Volo: p.flight_summary ?? "",
    Avvisi: (p.unmet ?? []).join(" · "),
    Link: p.booking_url ?? "",
  };
}

/**
 * Build and download an .xlsx workbook from the current results array.
 * Client-side only (Contract C3): no backend endpoint involved.
 */
export function exportPackagesXlsx(title: string, rows: PackageCardData[]): void {
  // When the rows span more than one distinct location, surface a "Località" column so the
  // workbook stays self-explanatory. With a single location the export is byte-for-byte as before.
  const multiLocation = new Set(rows.map(locationKey)).size > 1;

  const header = multiLocation ? ["Località", ...XLSX_HEADERS] : [...XLSX_HEADERS];
  const data = rows.map((p) =>
    multiLocation ? { "Località": locationOf(p), ...rowFor(p) } : rowFor(p),
  );

  const sheet = XLSX.utils.json_to_sheet(data, { header });
  const book = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(book, sheet, "Pacchetti");
  const safe = (title || "viaggio").replace(/[\\/:*?"<>|]+/g, "_");
  XLSX.writeFile(book, `${safe}.xlsx`);
}
