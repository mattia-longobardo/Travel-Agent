import { AlertTriangle, ArrowRight, CalendarDays, Hotel, House, Plane } from "lucide-react";
import {
  AccommodationViewButton,
  accommodationLabel,
  accommodationWarnings,
} from "@/components/AccommodationViewButton";
import type { PackageCardData } from "@/lib/types";

const BADGE_LABEL: Record<string, string> = {
  best_value: "Miglior valore",
  cheapest: "Più economico",
  upgrade: "Upgrade",
};

function formatDay(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("it-IT", { day: "2-digit", month: "short" });
}

function dateRange(from?: string | null, to?: string | null): string {
  const a = formatDay(from);
  const b = formatDay(to);
  if (a && b) return `${a} – ${b}`;
  return a || b;
}

function safeHttpUrl(url?: string | null): string | undefined {
  if (!url) return undefined;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" || parsed.protocol === "http:" ? parsed.toString() : undefined;
  } catch {
    return undefined;
  }
}

function BookingButton({ href, children, secondary = false }: {
  href?: string;
  children: React.ReactNode;
  secondary?: boolean;
}) {
  if (!href) {
    return (
      <span className="inline-flex min-h-12 flex-1 items-center justify-center rounded-lg bg-muted px-3 text-center text-sm text-muted-foreground">
        Non disponibile
      </span>
    );
  }
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={
        "inline-flex min-h-12 flex-1 items-center justify-center gap-2 rounded-lg px-3 text-center text-sm font-semibold transition " +
        (secondary
          ? "border border-[var(--travel-coral)] bg-background text-[var(--travel-coral)]"
          : "bg-[var(--travel-coral)] text-white shadow-sm")
      }
    >
      {children}
    </a>
  );
}

export function MobilePackageCard({ data }: { data: PackageCardData }) {
  const price = Math.round(data.price_per_person).toLocaleString("it-IT");
  const remote = !!data.image_url && /^https?:\/\//.test(data.image_url);
  const warnings = accommodationWarnings(data);
  const range = dateRange(data.date_from, data.date_to);
  const isSeparate = data.kind === "separate";
  const isHotelOnly = data.kind === "hotel_only";
  const isFlightOnly = data.kind === "flight_only";
  const accommodation = accommodationLabel(data);
  const AccommodationIcon = accommodation === "Casa" ? House : Hotel;
  const bookingHref = safeHttpUrl(data.booking_url);
  const hotelHref = safeHttpUrl(data.hotel_url) ?? (isHotelOnly ? bookingHref : undefined);
  const flightHref = safeHttpUrl(data.flight_url) ?? (isFlightOnly ? bookingHref : undefined);
  const flightLine = [data.departure_iata ? `da ${data.departure_iata}` : "", data.flight_summary || ""]
    .filter(Boolean)
    .join(" · ");
  const priceScope = isSeparate
    ? "stima volo + alloggio"
    : isHotelOnly
      ? `solo ${accommodation.toLowerCase()}`
      : isFlightOnly
        ? "solo volo"
        : `volo + ${accommodation.toLowerCase()}`;

  return (
    <article className="overflow-hidden rounded-2xl border bg-card shadow-sm">
      <div className="relative h-40 overflow-hidden bg-muted">
        <div
          className="travel-destination-thumb absolute inset-0 bg-cover bg-center"
          data-destination={remote ? undefined : data.badge || data.kind}
          style={remote ? { backgroundImage: `url(${data.image_url})` } : undefined}
          role="img"
          aria-label={data.destination}
        />
        <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/70 to-transparent" />
        {data.badge && (
          <span className="absolute left-3 top-3 rounded-full bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground shadow-sm">
            {BADGE_LABEL[data.badge] ?? data.badge}
          </span>
        )}
        <h3 className="absolute inset-x-4 bottom-3 break-words text-lg font-semibold leading-tight text-white">
          {data.destination}
        </h3>
      </div>

      <div className="flex flex-col gap-4 p-4">
        <div>
          <div className="flex flex-wrap items-end gap-x-2 gap-y-1">
            <span className="text-2xl font-bold leading-none">{price} {data.currency}</span>
            <span className="text-xs text-muted-foreground">a persona · {priceScope}</span>
          </div>
          {isSeparate && typeof data.flight_pp === "number" && typeof data.hotel_pp === "number" && (
            <p className="mt-1 text-xs text-muted-foreground">
              Volo {Math.round(data.flight_pp)}€ · {accommodation} {Math.round(data.hotel_pp)}€
            </p>
          )}
        </div>

        <div className="grid gap-2 rounded-xl bg-muted/60 p-3 text-sm">
          {!isFlightOnly && (
            <div className="flex min-w-0 items-start gap-2">
              <AccommodationIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-primary" />
              <span className="min-w-0 break-words font-medium">
                {data.hotel_name || (accommodation === "Casa" ? "Casa selezionata" : "Hotel selezionato")}
                {data.hotel_stars ? ` · ${data.hotel_stars}★` : ""}
              </span>
            </div>
          )}
          {!isHotelOnly && (
            <div className="flex min-w-0 items-start gap-2 text-muted-foreground">
              <Plane aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
              <span className="min-w-0 break-words">{flightLine || "Volo incluso"}</span>
            </div>
          )}
          <div className="flex min-w-0 items-center gap-2 text-muted-foreground">
            <CalendarDays aria-hidden="true" className="size-4 shrink-0" />
            <span>{isFlightOnly ? "Andata e ritorno" : `${data.nights} notti`}{range ? ` · ${range}` : ""}</span>
          </div>
        </div>

        {warnings.length > 0 && (
          <ul className="flex flex-col gap-1.5 rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs font-medium text-amber-800">
            {warnings.map((warning) => (
              <li key={warning} className="flex items-start gap-2">
                <AlertTriangle aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
                <span className="break-words">{warning}</span>
              </li>
            ))}
          </ul>
        )}

        {data.reason && <p className="break-words text-sm leading-6 text-muted-foreground">{data.reason}</p>}

        <div className="flex flex-col gap-2 border-t pt-4">
          {isSeparate ? (
            <div className="flex gap-2">
              <BookingButton href={hotelHref}>Prenota {accommodation.toLowerCase()}</BookingButton>
              <BookingButton href={flightHref} secondary>Prenota volo</BookingButton>
            </div>
          ) : (
            <BookingButton href={bookingHref}>
              {isFlightOnly ? "Prenota volo" : isHotelOnly ? `Prenota ${accommodation.toLowerCase()}` : "Vai all'offerta"}
              <ArrowRight aria-hidden="true" className="size-4" />
            </BookingButton>
          )}
          {!isFlightOnly && <AccommodationViewButton data={data} />}
        </div>
      </div>
    </article>
  );
}
