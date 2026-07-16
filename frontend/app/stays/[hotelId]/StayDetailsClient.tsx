"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  BedDouble,
  CalendarDays,
  Car,
  CheckCircle2,
  Clock,
  ExternalLink,
  House,
  Hotel,
  MapPin,
  Navigation,
  PawPrint,
  ShieldCheck,
  Star,
  Wifi,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

type PublicPolicyValue = string | number | boolean | null | Array<string | number | boolean>;

type PropertyDetails = {
  id: number;
  name: string | null;
  address: string | null;
  stars: number | null;
  check_in_time: string | null;
  check_out_time: string | null;
  description: string | null;
  gallery: string[];
  facilities: string[];
  policies: Record<string, PublicPolicyValue>;
  location: {
    lat: number;
    lng: number;
    label: string;
    source: "provider" | "nominatim";
    confidence: number;
  } | null;
  original_url: string | null;
  total_room_options: number;
  rooms: Array<{
    name?: string | null;
    meal_plan?: string | null;
    cancellation?: string | null;
    deposit_required?: boolean | null;
    price?: number | null;
    currency?: string | null;
    price_note?: string | null;
  }>;
};

type Query = {
  searchId?: string;
  dateFrom?: string;
  dateTo?: string;
  kind: "hotel" | "home";
  name?: string;
  destination?: string;
  destinationIata?: string;
  image?: string;
  stars?: number;
  rating?: number;
  reviews?: number;
  distanceKm?: number;
  facilities?: string[];
  cancellable?: boolean;
  nights?: number;
  pricePerPerson?: number;
  priceTotal?: number;
  currency?: string;
};

const MEAL_LABELS: Record<string, string> = {
  ROOM_ONLY: "Solo pernottamento",
  BED_BREAKFAST: "Colazione inclusa",
  HALF_BOARD: "Mezza pensione",
  FULL_BOARD: "Pensione completa",
  ALL_INCLUSIVE: "All inclusive",
};

const POLICY_LABELS: Record<string, { yes: string; no: string; icon: LucideIcon }> = {
  wifi_free: { yes: "Wi-Fi gratuito", no: "Wi-Fi non incluso", icon: Wifi },
  parking_available: { yes: "Parcheggio disponibile", no: "Parcheggio non disponibile", icon: Car },
  pets_allowed: { yes: "Animali ammessi", no: "Animali non ammessi", icon: PawPrint },
};

function labelMeal(value?: string | null) {
  if (!value) return null;
  return MEAL_LABELS[value] ?? value.replaceAll("_", " ").toLowerCase();
}

function safeHttpUrl(value?: string | null): string | undefined {
  if (!value) return undefined;
  try {
    const parsed = new URL(value);
    return parsed.protocol === "https:" || parsed.protocol === "http:" ? parsed.toString() : undefined;
  } catch {
    return undefined;
  }
}

function safeOriginalPropertyUrl(value?: string | null): string | undefined {
  const safe = safeHttpUrl(value);
  if (!safe) return undefined;
  const parsed = new URL(safe);
  const host = parsed.hostname.toLowerCase().replace(/\.$/, "");
  if (parsed.protocol !== "https:" || (host !== "lastminute.com" && !host.endsWith(".lastminute.com"))) {
    return undefined;
  }
  // Public property pages end in `_hid-<numeric id>`. Sales funnels such as `/s/tsx/...`
  // are deliberately rejected even when they carry `pageType=review`.
  if (!/^\/hotel\/.+_hid-\d+\/?$/i.test(parsed.pathname)) return undefined;
  if (parsed.search || parsed.hash) return undefined;
  return parsed.toString();
}

function normalizedRating(value?: number): number | undefined {
  if (value === undefined || !Number.isFinite(value) || value < 0) return undefined;
  return value > 10 && value <= 100 ? value / 10 : value <= 10 ? value : undefined;
}

function formatMoney(value?: number | null, currency = "EUR") {
  if (value === null || value === undefined || !Number.isFinite(value)) return null;
  try {
    return new Intl.NumberFormat("it-IT", { style: "currency", currency }).format(value);
  } catch {
    return `${value.toLocaleString("it-IT")} ${currency}`;
  }
}

function policyLabel(key: string, value: PublicPolicyValue): { text: string; icon: LucideIcon } | null {
  const known = POLICY_LABELS[key];
  if (known && typeof value === "boolean") {
    return { text: value ? known.yes : known.no, icon: known.icon };
  }
  if (value === null || value === "") return null;
  const label = key.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
  const rendered = Array.isArray(value) ? value.join(", ") : typeof value === "boolean" ? (value ? "Sì" : "No") : String(value);
  return { text: `${label}: ${rendered}`, icon: ShieldCheck };
}

export function StayDetailsClient({ hotelId, query }: { hotelId: string; query: Query }) {
  const canLoadDetails = hotelId !== "overview" && !!query.searchId && !!query.dateFrom && !!query.dateTo;
  const [details, setDetails] = useState<Partial<PropertyDetails> | null>(null);
  const [loading, setLoading] = useState(canLoadDetails);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [showAllRooms, setShowAllRooms] = useState(false);

  useEffect(() => {
    if (!canLoadDetails) return;
    let cancelled = false;
    const params = new URLSearchParams({
      search_id: query.searchId as string,
      date_from: query.dateFrom as string,
      date_to: query.dateTo as string,
    });
    if (query.destination) params.set("destination", query.destination);
    (async () => {
      try {
        const response = await fetch(`/api/properties/${encodeURIComponent(hotelId)}?${params}`, {
          credentials: "include",
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const payload = await response.json() as Partial<PropertyDetails>;
        if (!cancelled) setDetails(payload);
      } catch {
        // Live property details are optional enrichment. The search result already
        // contains enough information to render a useful, non-blocking page.
        if (!cancelled) setDetails(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [canLoadDetails, hotelId, query.dateFrom, query.dateTo, query.destination, query.searchId]);

  const isHome = query.kind === "home";
  const title = details?.name || query.name || (isHome ? "Casa vacanza" : "Hotel");
  const stars = details?.stars ?? query.stars ?? 0;
  const queryImage = safeHttpUrl(query.image);
  const gallery = details?.gallery?.length ? details.gallery : (queryImage ? [queryImage] : []);
  const heroImage = selectedImage && gallery.includes(selectedImage) ? selectedImage : gallery[0];
  const Icon = isHome ? House : Hotel;
  const rating = normalizedRating(query.rating);
  const facilities = Array.from(new Set([...(query.facilities || []), ...(details?.facilities || [])]));
  const policies = Object.entries(details?.policies || {})
    .map(([key, value]) => policyLabel(key, value))
    .filter((item): item is { text: string; icon: LucideIcon } => item !== null);
  const visibleRooms = showAllRooms ? (details?.rooms || []) : (details?.rooms || []).slice(0, 8);
  const providerHref = safeOriginalPropertyUrl(details?.original_url);

  return (
    <main className="min-h-dvh bg-muted/40 text-foreground">
      <header className="sticky top-0 z-20 border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex min-h-16 max-w-6xl items-center gap-3 px-4 md:px-8">
          <Link href="/" className="inline-flex min-h-11 items-center gap-2 rounded-lg px-3 text-sm font-semibold hover:bg-muted">
            <ArrowLeft aria-hidden="true" className="size-4" /> Torna ai risultati
          </Link>
          <span className="ml-auto rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
            Scheda struttura
          </span>
        </div>
      </header>

      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6 md:px-8 md:py-10">
        {heroImage && (
          <section aria-label={`Galleria di ${title}`} className="overflow-hidden rounded-2xl border bg-card shadow-sm">
            <div className="relative h-[22rem] bg-muted md:h-[30rem]">
              {/* Provider images are arbitrary remote hosts, so they intentionally bypass next/image. */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={heroImage} alt={title} className="h-full w-full object-cover" />
              <span className="absolute bottom-3 right-3 rounded-full bg-black/70 px-3 py-1 text-xs font-semibold text-white">
                {gallery.length} foto
              </span>
            </div>
            {gallery.length > 1 && (
              <div className="flex gap-2 overflow-x-auto p-3">
                {gallery.map((src, index) => (
                  <button
                    type="button"
                    key={src}
                    onClick={() => setSelectedImage(src)}
                    aria-label={`Mostra foto ${index + 1}`}
                    aria-pressed={src === heroImage}
                    className="h-20 w-28 shrink-0 overflow-hidden rounded-lg border-2 data-[active=true]:border-primary"
                    data-active={src === heroImage}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={src} alt="" className="h-full w-full object-cover" />
                  </button>
                ))}
              </div>
            )}
          </section>
        )}

        <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="flex flex-col gap-6 rounded-2xl border bg-card p-5 shadow-sm md:p-7">
            <div>
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-primary">
                <Icon aria-hidden="true" className="size-5" /> {isHome ? "Casa e affitto breve" : "Hotel e resort"}
              </div>
              <h1 className="text-3xl font-bold tracking-tight md:text-4xl">{title}</h1>
              <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2">
                {stars > 0 && (
                  <div className="flex items-center gap-1 text-amber-600" aria-label={`${stars} stelle`}>
                    {Array.from({ length: Math.min(stars, 5) }, (_, i) => <Star key={i} className="size-4 fill-current" />)}
                  </div>
                )}
                {rating !== undefined && (
                  <div className="rounded-full bg-primary/10 px-3 py-1 text-sm font-semibold text-primary">
                    {rating.toLocaleString("it-IT", { maximumFractionDigits: 1 })}/10
                    {query.reviews !== undefined && ` · ${query.reviews.toLocaleString("it-IT")} recensioni`}
                  </div>
                )}
              </div>
              {(details?.address || query.destination) && (
                <p className="mt-3 flex items-start gap-2 text-sm text-muted-foreground">
                  <MapPin aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
                  {details?.address || query.destination}
                </p>
              )}
            </div>

            {loading && <div className="h-24 animate-pulse rounded-xl bg-muted" aria-label="Caricamento dettagli" />}

            {(query.distanceKm !== undefined || query.cancellable !== undefined) && (
              <div className="grid gap-3 sm:grid-cols-2">
                {query.distanceKm !== undefined && <Feature icon={Navigation} text={`${query.distanceKm.toLocaleString("it-IT")} km dal centro`} />}
                {query.cancellable !== undefined && (
                  <Feature
                    icon={ShieldCheck}
                    text={query.cancellable ? "Opzione cancellabile disponibile" : "Tariffa mostrata non cancellabile"}
                  />
                )}
              </div>
            )}

            {details?.description && (
              <div>
                <h2 className="text-lg font-semibold">La struttura</h2>
                <p className="mt-2 leading-7 text-muted-foreground">{details.description}</p>
              </div>
            )}

            {facilities.length > 0 && (
              <div>
                <h2 className="text-lg font-semibold">Servizi</h2>
                <div className="mt-3 flex flex-wrap gap-2">
                  {facilities.map((facility) => (
                    <span key={facility} className="inline-flex items-center gap-1.5 rounded-full bg-muted px-3 py-2 text-sm">
                      <CheckCircle2 className="size-4 text-primary" /> {facility}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {(policies.length > 0 || details?.check_in_time || details?.check_out_time) && (
              <div>
                <h2 className="text-lg font-semibold">Policy e informazioni</h2>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  {policies.map((policy) => <Feature key={policy.text} icon={policy.icon} text={policy.text} />)}
                  {details?.check_in_time && <Feature icon={Clock} text={`Check-in dalle ${details.check_in_time}`} />}
                  {details?.check_out_time && <Feature icon={Clock} text={`Check-out entro le ${details.check_out_time}`} />}
                </div>
              </div>
            )}

            {details?.rooms?.length ? (
              <div>
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h2 className="text-lg font-semibold">Sistemazioni disponibili</h2>
                  <span className="text-xs text-muted-foreground">
                    {details.total_room_options || details.rooms.length} opzioni dal provider
                  </span>
                </div>
                <div className="mt-3 grid gap-3">
                  {visibleRooms.map((room, index) => {
                    const price = formatMoney(room.price, room.currency || query.currency || "EUR");
                    return (
                      <div key={`${room.name}-${index}`} className="rounded-xl border bg-background p-4">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div className="flex items-center gap-2 font-semibold"><BedDouble className="size-4 text-primary" />{room.name || "Camera"}</div>
                          {price && <div className="font-semibold text-primary">{price}</div>}
                        </div>
                        <div className="mt-2 grid gap-1 text-sm text-muted-foreground">
                          {labelMeal(room.meal_plan) && <div>{labelMeal(room.meal_plan)}</div>}
                          {room.cancellation && <div>{room.cancellation}</div>}
                          {room.deposit_required !== null && room.deposit_required !== undefined && (
                            <div>{room.deposit_required ? "Deposito richiesto" : "Nessun deposito richiesto"}</div>
                          )}
                          {room.price_note && <div className="text-xs">{room.price_note}</div>}
                        </div>
                      </div>
                    );
                  })}
                </div>
                {(details.rooms.length > 8) && (
                  <button
                    type="button"
                    onClick={() => setShowAllRooms((value) => !value)}
                    className="mt-3 min-h-11 w-full rounded-lg border px-4 text-sm font-semibold hover:bg-muted"
                  >
                    {showAllRooms ? "Mostra meno opzioni" : `Mostra tutte le ${details.rooms.length} opzioni`}
                  </button>
                )}
              </div>
            ) : null}

            <PropertyMap
              location={details?.location || null}
              address={details?.address}
              title={title}
              destination={query.destination}
            />
          </div>

          <aside className="h-fit rounded-2xl border bg-card p-5 shadow-sm lg:sticky lg:top-24">
            <h2 className="font-semibold">Il soggiorno cercato</h2>
            <div className="mt-4 flex flex-col gap-3 text-sm">
              {(query.dateFrom || query.dateTo) && (
                <div className="flex items-start gap-2"><CalendarDays className="mt-0.5 size-4 text-primary" />{query.dateFrom} – {query.dateTo}</div>
              )}
              {query.nights !== undefined && <div>{query.nights} {query.nights === 1 ? "notte" : "notti"}</div>}
              {query.pricePerPerson !== undefined && (
                <div>Da <strong>{formatMoney(query.pricePerPerson, query.currency || "EUR")}</strong> a persona</div>
              )}
              {query.priceTotal !== undefined && (
                <div>Totale indicativo: <strong>{formatMoney(query.priceTotal, query.currency || "EUR")}</strong></div>
              )}
            </div>
            {providerHref && (
              <a
                href={providerHref}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-5 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-lg bg-[var(--travel-coral)] px-4 text-center text-sm font-semibold text-white hover:bg-[var(--travel-coral-dark)]"
              >
                Apri la pagina su lastminute.com <ExternalLink className="size-4" />
              </a>
            )}
            <p className="mt-5 border-t pt-4 text-xs leading-5 text-muted-foreground">
              Questa scheda è informativa. Disponibilità finale e prenotazione restano sul sito del provider.
            </p>
          </aside>
        </section>
      </div>
    </main>
  );
}

function Feature({ icon: Icon, text }: { icon: LucideIcon; text: string }) {
  return <div className="flex items-center gap-2 rounded-xl bg-muted/60 p-3 text-sm"><Icon className="size-4 shrink-0 text-primary" />{text}</div>;
}

function PropertyMap({
  location,
  address,
  title,
  destination,
}: {
  location: PropertyDetails["location"];
  address?: string | null;
  title: string;
  destination?: string;
}) {
  const textualQuery = [title, address, destination]
    .filter((value): value is string => typeof value === "string" && value.trim().length > 0)
    .join(", ");
  const coordinateQuery = location && Number.isFinite(location.lat) && Number.isFinite(location.lng)
    ? `${location.lat},${location.lng}`
    : null;
  // The normal Google Maps embed endpoint is interactive and does not require an API key.
  // When verified coordinates are unavailable, searching by property name + address still
  // renders a useful map instead of replacing it with a non-interactive outbound link.
  const mapQuery = coordinateQuery || textualQuery;

  if (!mapQuery) return null;

  const embed = `https://www.google.com/maps?${new URLSearchParams({
    q: mapQuery,
    z: "16",
    output: "embed",
  }).toString()}`;
  const external = `https://www.google.com/maps/search/?${new URLSearchParams({
    api: "1",
    query: mapQuery,
  }).toString()}`;
  const directions = `https://www.google.com/maps/dir/?${new URLSearchParams({
    api: "1",
    destination: mapQuery,
  }).toString()}`;

  return (
    <section>
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><MapPin className="size-5 text-primary" /> Posizione</h2>
        {location && (
          <span className="text-xs text-muted-foreground">
            {location.source === "provider" ? "Coordinate del provider" : "Posizione ricavata dall’indirizzo"}
          </span>
        )}
      </div>
      <div className="overflow-hidden rounded-2xl border bg-muted">
        <iframe
          src={embed}
          title={`Mappa interattiva di ${title}`}
          loading="lazy"
          referrerPolicy="no-referrer-when-downgrade"
          allowFullScreen
          className="h-[24rem] w-full"
        />
      </div>
      {!location && (
        <p className="mt-2 text-xs text-muted-foreground">
          La struttura viene cercata sulla mappa tramite nome e indirizzo; verifica il marker prima di usare le indicazioni.
        </p>
      )}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-sm">
        <span className="text-xs text-muted-foreground">{location?.label || address || destination || title}</span>
        <span className="flex flex-wrap gap-2">
          <a href={external} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-10 items-center gap-2 rounded-lg border bg-background px-3 font-semibold text-primary hover:bg-muted">
            Apri in Google Maps <ExternalLink className="size-4" />
          </a>
          <a href={directions} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-10 items-center gap-2 rounded-lg border bg-background px-3 font-semibold text-primary hover:bg-muted">
            Indicazioni <Navigation className="size-4" />
          </a>
        </span>
      </div>
    </section>
  );
}
