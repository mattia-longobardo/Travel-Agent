import Image from "next/image";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, ArrowRight, Hotel, House, Plane, Star } from "lucide-react";
import type { PackageCardData } from "@/lib/types";
import {
  AccommodationViewButton,
  accommodationLabel,
  accommodationWarnings,
} from "@/components/AccommodationViewButton";

const BADGE_LABEL: Record<string, string> = {
  best_value: "Miglior valore",
  cheapest: "Più economico",
  upgrade: "Upgrade",
};

const DESTINATION_IMAGES = [
  { pattern: /azzorre|azores|ponta|pdl|sao|são/i, src: "/travel/azores-lagoon.png" },
  { pattern: /canarie|canary|tenerife|gran canaria|lanzarote|fuerteventura|tfs|lpa|ace|fue/i, src: "/travel/canary-coast.png" },
  { pattern: /baleari|maiorca|mallorca|palma|pmi|minorca|ibiza|grecia|greece|rodi|rho|creta|crete|sicil|sardegn|mare|spiagg|beach/i, src: "/travel/canary-coast.png" },
  { pattern: /lisbona|lisbon|opo|porto|portogallo|madeira|funchal|fnc/i, src: "/travel/lisbon-river.png" },
];

function imageForDestination(destination: string) {
  return (
    DESTINATION_IMAGES.find((item) => item.pattern.test(destination))?.src ||
    "/travel/azores-lagoon.png"
  );
}

function isRemote(url?: string | null): url is string {
  return !!url && /^https?:\/\//.test(url);
}

// Only allow http(s) links as an href — a hostile data source could otherwise smuggle
// a `javascript:` URL. Returns the first valid url, or undefined if none qualify.
function safeHref(...urls: (string | null | undefined)[]): string | undefined {
  for (const url of urls) {
    if (url && /^https?:\/\//.test(url)) return url;
  }
  return undefined;
}

function formatDay(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("it-IT", { day: "2-digit", month: "short" });
}

function formatDateRange(from?: string | null, to?: string | null): string {
  const a = formatDay(from);
  const b = formatDay(to);
  if (a && b) return `${a} – ${b}`;
  return a || b;
}

function badgeClass(badge: PackageCardData["badge"]) {
  if (badge === "upgrade") {
    return "bg-[var(--travel-coral)] text-white";
  }
  if (badge === "cheapest") {
    return "bg-secondary text-secondary-foreground";
  }
  return "bg-primary text-primary-foreground";
}

export function PackageCard({ data }: { data: PackageCardData }) {
  const price = Math.round(data.price_per_person).toLocaleString("it-IT");
  const remote = isRemote(data.image_url);
  const fallback = imageForDestination(data.destination);
  const dateRange = formatDateRange(data.date_from, data.date_to);
  const accommodation = accommodationLabel(data);
  const warnings = accommodationWarnings(data);
  const flightLine = [data.departure_iata ? `da ${data.departure_iata}` : "", data.flight_summary || ""]
    .filter(Boolean)
    .join(" · ");

  // Separate cards: the headline price is a flight+hotel estimate with no single
  // combined checkout, so offer two real booking actions (hotel + flight) that each
  // match their own sub-price. Fall back to one CTA when neither sub-link is present.
  const isSeparate = data.kind === "separate";
  // Single-service cards: hide the row of the service that was not searched, and label
  // the price scope so a flight-only price is never mistaken for a full trip price.
  const isHotelOnly = data.kind === "hotel_only";
  const isFlightOnly = data.kind === "flight_only";
  const priceScope = isSeparate
    ? ` · stima volo + ${accommodation.toLowerCase()}`
    : isHotelOnly
      ? ` · solo ${accommodation.toLowerCase()}`
      : isFlightOnly
        ? " · solo volo"
        : "";
  const hotelHref = safeHref(data.hotel_url, data.booking_url);
  const flightHref = safeHref(data.flight_url);
  const hasDualCtas = isSeparate && (isRemote(data.hotel_url) || isRemote(data.flight_url));
  const bookingHref = safeHref(data.booking_url);
  const showBreakdown =
    isSeparate &&
    typeof data.flight_pp === "number" &&
    typeof data.hotel_pp === "number";

  const AccommodationIcon = accommodation === "Casa" ? House : Hotel;

  return (
    <Card className="flex w-[22rem] shrink-0 flex-col gap-0 overflow-hidden rounded-lg border bg-card py-0 shadow-sm">
      <div className="relative aspect-[16/9] shrink-0 overflow-hidden">
        {remote ? (
          // The offer's own photo: an arbitrary remote URL, so render directly (no
          // next/image optimizer/remote-pattern config, no open-proxy surface).
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={data.image_url as string}
            alt={data.destination}
            className="absolute inset-0 h-full w-full object-cover"
          />
        ) : (
          <Image src={fallback} alt={data.destination} fill sizes="352px" className="object-cover" />
        )}
        {data.badge && (
          <Badge className={`absolute left-3 top-3 ${badgeClass(data.badge)}`}>
            {BADGE_LABEL[data.badge]}
          </Badge>
        )}
      </div>
      <CardHeader className="shrink-0 gap-1.5 pt-4">
        <CardTitle className="min-w-0 break-words text-base font-semibold leading-tight">
          {data.destination}
        </CardTitle>
        <div className="flex flex-wrap items-baseline gap-x-1.5 gap-y-0.5">
          <span className="text-xl font-semibold leading-none">
            {price} {data.currency}
          </span>
          <span className="text-xs text-muted-foreground">
            a persona{priceScope}
          </span>
        </div>
        {showBreakdown ? (
          <div className="text-xs text-muted-foreground">
            Volo {Math.round(data.flight_pp as number)}€ · {accommodation} {Math.round(data.hotel_pp as number)}€ a persona
          </div>
        ) : null}
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-3 pt-3">
        <div className="grid gap-2 text-sm">
          {!isFlightOnly && (
            <div className="flex min-w-0 items-start gap-2 text-muted-foreground">
              <AccommodationIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
              <span className="min-w-0 break-words">
                {data.hotel_name || (accommodation === "Casa" ? "Casa selezionata" : "Hotel selezionato")}
                {data.hotel_stars ? ` · ${data.hotel_stars} stelle` : ""}
                {data.hotel_rating ? ` · ${data.hotel_rating}` : ""}
              </span>
            </div>
          )}
          {!isHotelOnly && (
            <div className="flex min-w-0 items-start gap-2 text-muted-foreground">
              <Plane aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
              <span className="min-w-0 break-words">
                {flightLine || (isFlightOnly ? "Volo" : "Volo incluso")}
              </span>
            </div>
          )}
          <div className="flex min-w-0 items-start gap-2 text-muted-foreground">
            <Star aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            <span className="min-w-0 break-words">
              {isFlightOnly ? "Andata e ritorno" : `${data.nights} notti`}
              {dateRange ? ` · ${dateRange}` : ""}
            </span>
          </div>
        </div>
        {warnings.length > 0 ? (
          <ul className="flex flex-col gap-1 rounded-md border border-amber-300 bg-amber-50 p-2 text-xs text-amber-800">
            {warnings.map((w) => (
              <li key={w} className="flex items-start gap-1.5">
                <AlertTriangle aria-hidden="true" className="mt-0.5 size-3.5 shrink-0" />
                <span className="break-words">{w}</span>
              </li>
            ))}
          </ul>
        ) : null}
        {data.reason ? (
          <p className="flex-1 break-words text-sm leading-6 text-muted-foreground">
            {data.reason}
          </p>
        ) : null}
      </CardContent>
      <CardFooter className="mt-auto shrink-0 flex-col gap-2 border-t bg-muted/40 p-3">
        {hasDualCtas ? (
          <div className="flex w-full gap-2">
            {hotelHref ? (
              <a href={hotelHref} target="_blank" rel="noopener noreferrer"
                className="inline-flex min-h-10 flex-1 items-center justify-center gap-1.5 rounded-lg bg-[var(--travel-coral)] px-3 text-sm font-medium text-white transition hover:bg-[var(--travel-coral-dark)]">
                Prenota {accommodation.toLowerCase()}
              </a>
            ) : (
              <span className="inline-flex min-h-10 flex-1 items-center justify-center rounded-lg bg-muted px-3 text-sm text-muted-foreground">Alloggio non disponibile</span>
            )}
            {flightHref ? (
              <a href={flightHref} target="_blank" rel="noopener noreferrer"
                className="inline-flex min-h-10 flex-1 items-center justify-center gap-1.5 rounded-lg border border-[var(--travel-coral)] px-3 text-sm font-medium text-[var(--travel-coral)] transition hover:bg-[var(--travel-coral)]/10">
                Prenota volo
              </a>
            ) : (
              <span className="inline-flex min-h-10 flex-1 items-center justify-center rounded-lg border px-3 text-sm text-muted-foreground">Volo non disponibile</span>
            )}
          </div>
        ) : bookingHref ? (
          <a href={bookingHref} target="_blank" rel="noopener noreferrer"
            className="inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg bg-[var(--travel-coral)] px-3 text-sm font-medium text-white transition hover:bg-[var(--travel-coral-dark)]">
            {isFlightOnly ? "Prenota volo" : isHotelOnly ? `Prenota ${accommodation.toLowerCase()}` : "Vai all'offerta"}
            <ArrowRight aria-hidden="true" className="size-4" />
          </a>
        ) : (
          <span className="inline-flex min-h-10 w-full items-center justify-center rounded-lg bg-muted px-3 text-sm text-muted-foreground">
            Offerta non disponibile
          </span>
        )}
        {!isFlightOnly && <AccommodationViewButton data={data} />}
      </CardFooter>
    </Card>
  );
}
