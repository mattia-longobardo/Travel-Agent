import { ExternalLink, Hotel, House } from "lucide-react";
import type { PackageCardData } from "@/lib/types";

function safeHttpUrl(url?: string | null): string | undefined {
  if (!url) return undefined;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" || parsed.protocol === "http:" ? parsed.toString() : undefined;
  } catch {
    return undefined;
  }
}

function internalPresentationFromProvider(url?: string | null, kind: "hotel" | "home" = "hotel"): string | undefined {
  if (!url) return undefined;
  if (url.startsWith("/stays/")) return url;
  const safe = safeHttpUrl(url);
  if (!safe) return undefined;
  const parsed = new URL(safe);
  const match = parsed.pathname.match(/\/s\/tsx\/([^/]+)$/i);
  const searchId = parsed.searchParams.get("vcSearchId");
  const dateFrom = parsed.searchParams.get("dateFrom");
  const dateTo = parsed.searchParams.get("dateTo");
  if (!match || !searchId || !dateFrom || !dateTo) return undefined;
  const query = new URLSearchParams({ search_id: searchId, date_from: dateFrom, date_to: dateTo, kind });
  return `/stays/${encodeURIComponent(match[1])}?${query.toString()}`;
}

function withCardContext(href: string, data: PackageCardData, kind: "hotel" | "home"): string {
  const parsed = new URL(href, "https://travel.internal");
  const params = parsed.searchParams;
  const set = (key: string, value: string | number | null | undefined) => {
    if (value !== null && value !== undefined && String(value) !== "") params.set(key, String(value));
  };

  set("name", data.hotel_name);
  set("destination", data.dest_name || data.destination);
  set("destination_iata", data.dest_iata);
  set("kind", kind);
  set("image", data.image_url);
  set("stars", data.hotel_stars);
  set("rating", data.hotel_rating);
  set("reviews", data.hotel_reviews);
  set("distance_km", data.hotel_distance_km);
  if (data.hotel_facilities?.length) params.set("facilities", JSON.stringify(data.hotel_facilities));
  if (data.hotel_cancellable !== null && data.hotel_cancellable !== undefined) {
    params.set("cancellable", data.hotel_cancellable ? "1" : "0");
  }
  set("date_from", data.date_from);
  set("date_to", data.date_to);
  set("nights", data.nights);
  set("price_per_person", data.price_per_person);
  set("price_total", data.price_total);
  set("currency", data.currency);
  return `${parsed.pathname}${params.size ? `?${params.toString()}` : ""}`;
}

export function accommodationLabel(data: PackageCardData): "Hotel" | "Casa" {
  return data.accommodation_kind === "home" ? "Casa" : "Hotel";
}

export function accommodationWarnings(data: PackageCardData): string[] {
  const warnings = data.unmet ?? [];
  if (data.accommodation_kind !== "home") return warnings;
  // Persisted result batches may predate the backend fix and still contain an hotel-star
  // warning for a house/apartment. Keep every other warning, especially budget violations.
  return warnings.filter((warning) => !/(?:★|\bstell(?:a|e)\b|\bstars?\b)/i.test(warning));
}

export function accommodationDetailHref(data: PackageCardData): string | undefined {
  if (data.kind === "flight_only") return undefined;
  const kind = data.accommodation_kind === "home" ? "home" : "hotel";
  const stable = internalPresentationFromProvider(data.property_url, kind)
    ?? internalPresentationFromProvider(data.review_url, kind);
  if (stable) return withCardContext(stable, data, kind);
  // Legacy cards may lack provider identifiers. They still open an internal overview made
  // from persisted card data, never the provider's sales/checkout funnel.
  return withCardContext("/stays/overview", data, kind);
}

export function AccommodationViewButton({
  data,
  compact = false,
}: {
  data: PackageCardData;
  compact?: boolean;
}) {
  const href = accommodationDetailHref(data);
  if (!href) return null;
  const label = accommodationLabel(data);
  const Icon = label === "Casa" ? House : Hotel;

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={
        "inline-flex w-full items-center justify-center gap-2 rounded-lg border-2 border-primary bg-background font-semibold text-primary shadow-sm transition hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring " +
        (compact ? "min-h-10 px-2 text-xs" : "min-h-11 px-4 text-sm")
      }
    >
      <Icon aria-hidden="true" className={compact ? "size-3.5" : "size-4"} />
      Vedi {label}
      <ExternalLink aria-hidden="true" className={compact ? "size-3" : "size-3.5"} />
    </a>
  );
}
