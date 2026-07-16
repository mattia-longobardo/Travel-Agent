import type { PackageCardData } from "@/lib/types";

export interface LocationGroup {
  key: string;
  label: string;
  items: PackageCardData[];
}

// Pull a 3-letter IATA-ish code out of a destination string like
// "Creta (Heraklion) (HER)" → "HER". Falls back to null when none is present.
function parseIata(destination: string): string | null {
  const matches = destination.match(/\(([A-Z]{3})\)/g);
  if (!matches || matches.length === 0) return null;
  const last = matches[matches.length - 1];
  return last.slice(1, 4);
}

// Stable key used to bucket a card into a location group.
export function locationKey(p: PackageCardData): string {
  const iata = p.dest_iata?.trim();
  if (iata) return iata.toUpperCase();
  const parsed = parseIata(p.destination ?? "");
  if (parsed) return parsed;
  return (p.dest_name ?? p.destination ?? "").trim() || "—";
}

function locationLabel(p: PackageCardData): string {
  return (p.dest_name?.trim() || p.destination?.trim() || p.dest_iata?.trim() || "—");
}

// Group packages by location, preserving first-seen order of both groups and items.
export function groupByLocation(packages: PackageCardData[]): LocationGroup[] {
  const order: string[] = [];
  const map = new Map<string, LocationGroup>();
  for (const p of packages) {
    const key = locationKey(p);
    let group = map.get(key);
    if (!group) {
      group = { key, label: locationLabel(p), items: [] };
      map.set(key, group);
      order.push(key);
    }
    group.items.push(p);
  }
  return order.map((k) => map.get(k)!);
}
