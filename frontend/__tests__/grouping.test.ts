import { groupByLocation } from "@/lib/grouping";
import type { PackageCardData } from "@/lib/types";

function pkg(p: Partial<PackageCardData> & { id: string }): PackageCardData {
  return {
    kind: "package",
    badge: null,
    destination: "Tenerife (TFS)",
    price_per_person: 500,
    price_total: 1000,
    currency: "EUR",
    nights: 7,
    ...p,
  };
}

test("groups by dest_iata, preserving first-seen order", () => {
  const groups = groupByLocation([
    pkg({ id: "1", dest_iata: "HER", dest_name: "Creta", destination: "Creta (HER)" }),
    pkg({ id: "2", dest_iata: "TFS", dest_name: "Tenerife", destination: "Tenerife (TFS)" }),
    pkg({ id: "3", dest_iata: "HER", dest_name: "Creta", destination: "Creta (HER)" }),
  ]);
  expect(groups.map((g) => g.key)).toEqual(["HER", "TFS"]);
  expect(groups.map((g) => g.label)).toEqual(["Creta", "Tenerife"]);
  expect(groups[0].items.map((i) => i.id)).toEqual(["1", "3"]);
  expect(groups[1].items.map((i) => i.id)).toEqual(["2"]);
});

test("falls back to IATA parsed from the destination string when dest_iata is absent", () => {
  const groups = groupByLocation([
    pkg({ id: "1", destination: "Creta (Heraklion) (HER)" }),
    pkg({ id: "2", destination: "Tenerife (TFS)" }),
    pkg({ id: "3", destination: "Creta (Heraklion) (HER)" }),
  ]);
  expect(groups.map((g) => g.key)).toEqual(["HER", "TFS"]);
  expect(groups[0].items.map((i) => i.id)).toEqual(["1", "3"]);
});

test("single location returns one group", () => {
  const groups = groupByLocation([
    pkg({ id: "1", dest_iata: "TFS" }),
    pkg({ id: "2", dest_iata: "TFS" }),
  ]);
  expect(groups).toHaveLength(1);
  expect(groups[0].items).toHaveLength(2);
});
