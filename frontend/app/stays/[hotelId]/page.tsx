import { StayDetailsClient } from "./StayDetailsClient";

type SearchParams = Record<string, string | string[] | undefined>;

function one(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function number(value: string | string[] | undefined): number | undefined {
  const parsed = Number(one(value));
  return Number.isFinite(parsed) ? parsed : undefined;
}

function boolean(value: string | string[] | undefined): boolean | undefined {
  const parsed = one(value);
  if (parsed === "1") return true;
  if (parsed === "0") return false;
  return undefined;
}

function facilities(value: string | string[] | undefined): string[] {
  try {
    const parsed: unknown = JSON.parse(one(value) || "[]");
    return Array.isArray(parsed)
      ? parsed.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
      : [];
  } catch {
    return [];
  }
}

export default async function StayPage({
  params,
  searchParams,
}: {
  params: Promise<{ hotelId: string }>;
  searchParams: Promise<SearchParams>;
}) {
  const [{ hotelId }, query] = await Promise.all([params, searchParams]);
  return (
    <StayDetailsClient
      hotelId={hotelId}
      query={{
        searchId: one(query.search_id),
        dateFrom: one(query.date_from),
        dateTo: one(query.date_to),
        kind: one(query.kind) === "home" ? "home" : "hotel",
        name: one(query.name),
        destination: one(query.destination),
        destinationIata: one(query.destination_iata),
        image: one(query.image),
        stars: number(query.stars),
        rating: number(query.rating),
        reviews: number(query.reviews),
        distanceKm: number(query.distance_km),
        facilities: facilities(query.facilities),
        cancellable: boolean(query.cancellable),
        nights: number(query.nights),
        pricePerPerson: number(query.price_per_person),
        priceTotal: number(query.price_total),
        currency: one(query.currency),
      }}
    />
  );
}
