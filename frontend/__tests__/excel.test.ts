import { vi } from "vitest";
import * as XLSX from "xlsx";
import { exportPackagesXlsx, XLSX_HEADERS } from "@/lib/excel";
import type { PackageCardData } from "@/lib/types";

// xlsx's `writeFile` performs a real filesystem/DOM write — stub just that one
// export while keeping the real `utils` so we can inspect the built worksheet.
vi.mock("xlsx", async (importActual) => {
  const actual = await importActual<typeof import("xlsx")>();
  return { ...actual, writeFile: vi.fn() };
});

const card: PackageCardData = {
  id: "pkg-1",
  kind: "package",
  badge: "best_value",
  destination: "Tenerife (TFS)",
  departure_iata: "MXP",
  price_per_person: 690,
  price_total: 1380,
  currency: "EUR",
  nights: 7,
  date_from: "2026-08-18",
  date_to: "2026-08-25",
  hotel_name: "Hotel Sol",
  hotel_stars: 4,
  hotel_rating: 8.6,
  flight_summary: "MXP → TFS",
  unmet: ["Supera il budget di 120€ a persona"],
  booking_url: "https://book.example/offer/1",
};

test("builds a worksheet with the expected headers and triggers a download", () => {
  const writeFile = vi.mocked(XLSX.writeFile);
  writeFile.mockClear();

  exportPackagesXlsx("La mia ricerca", [card]);

  expect(writeFile).toHaveBeenCalledTimes(1);
  const [workbook, filename] = writeFile.mock.calls[0];
  // Filename uses the sanitized title.
  expect(filename).toBe("La mia ricerca.xlsx");

  const sheet = workbook.Sheets[workbook.SheetNames[0]];
  const rows = XLSX.utils.sheet_to_json(sheet, { header: 1 }) as unknown[][];
  const headers = rows[0] as string[];
  for (const h of XLSX_HEADERS) expect(headers).toContain(h);

  // Round-trip the data row and confirm the booking link cell is present.
  const records = XLSX.utils.sheet_to_json(sheet) as Record<string, unknown>[];
  expect(records[0].Link).toBe("https://book.example/offer/1");
  expect(records[0].Partenza).toBe("MXP");
  expect(records[0].Avvisi).toBe("Supera il budget di 120€ a persona");
});

test("single location: no 'Località' column (headers identical to today)", () => {
  const writeFile = vi.mocked(XLSX.writeFile);
  writeFile.mockClear();

  // Two cards but the SAME location.
  const second: PackageCardData = {
    ...card,
    id: "pkg-2",
    badge: "cheapest",
    hotel_name: "Hotel Luna",
  };

  exportPackagesXlsx("La mia ricerca", [card, second]);

  const [workbook] = writeFile.mock.calls[0];
  const sheet = workbook.Sheets[workbook.SheetNames[0]];
  const rows = XLSX.utils.sheet_to_json(sheet, { header: 1 }) as unknown[][];
  const headers = rows[0] as string[];

  expect(headers).not.toContain("Località");
  // Headers are exactly today's static set, in order.
  expect(headers).toEqual([...XLSX_HEADERS]);
});

test("multiple locations: adds a 'Località' column with per-row values", () => {
  const writeFile = vi.mocked(XLSX.writeFile);
  writeFile.mockClear();

  const tenerife: PackageCardData = {
    ...card,
    id: "pkg-tfs",
    dest_iata: "TFS",
    dest_name: "Tenerife",
    destination: "Tenerife (TFS)",
  };
  const crete: PackageCardData = {
    ...card,
    id: "pkg-her",
    dest_iata: "HER",
    dest_name: "Creta",
    destination: "Creta (HER)",
  };

  exportPackagesXlsx("Multi", [tenerife, crete]);

  const [workbook] = writeFile.mock.calls[0];
  const sheet = workbook.Sheets[workbook.SheetNames[0]];
  const rows = XLSX.utils.sheet_to_json(sheet, { header: 1 }) as unknown[][];
  const headers = rows[0] as string[];

  expect(headers).toContain("Località");
  // All original headers are still present.
  for (const h of XLSX_HEADERS) expect(headers).toContain(h);

  const records = XLSX.utils.sheet_to_json(sheet) as Record<string, unknown>[];
  expect(records[0]["Località"]).toBe("Tenerife");
  expect(records[1]["Località"]).toBe("Creta");
});

test("multiple locations distinguished by dest_iata fall back to destination for the label", () => {
  const writeFile = vi.mocked(XLSX.writeFile);
  writeFile.mockClear();

  // No dest_name, distinct by dest_iata; label should come from destination.
  const a: PackageCardData = { ...card, id: "a", dest_iata: "TFS", destination: "Tenerife (TFS)" };
  const b: PackageCardData = { ...card, id: "b", dest_iata: "HER", destination: "Creta (HER)" };

  exportPackagesXlsx("Multi", [a, b]);

  const [workbook] = writeFile.mock.calls[0];
  const sheet = workbook.Sheets[workbook.SheetNames[0]];
  const records = XLSX.utils.sheet_to_json(sheet) as Record<string, unknown>[];
  expect(records[0]["Località"]).toBe("Tenerife (TFS)");
  expect(records[1]["Località"]).toBe("Creta (HER)");
});
