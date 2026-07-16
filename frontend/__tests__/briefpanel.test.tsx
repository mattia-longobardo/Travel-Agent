import { render, screen } from "@testing-library/react";
import { BriefPanel } from "@/components/BriefPanel";

import type { BriefData } from "@/lib/types";

const baseBrief: BriefData = {
  destination_hint: "mare", date_from: "2026-08-16", date_to: "2026-08-23",
  window_from: null, window_to: null, trip_nights: null, dates_flexible: false,
  adults: 2, children_ages: [], budget_per_person: 800, currency: "EUR",
  min_stars: 4, origin_iata: ["MXP"],
};

test("renders available brief fields", () => {
  render(<BriefPanel brief={baseBrief} />);
  expect(screen.getByText("mare")).toBeInTheDocument();
  expect(screen.getByText("MXP")).toBeInTheDocument();
  expect(screen.getByText(/800/)).toBeInTheDocument();
  expect(screen.getByText("★4+")).toBeInTheDocument();
});

test("renders the explicit search mode and accommodation choice", () => {
  render(<BriefPanel brief={{ ...baseBrief, search_mode: "hotel_only", accommodation_type: "both" }} />);
  expect(screen.getByText("Solo alloggio")).toBeInTheDocument();
  expect(screen.getByText("Hotel e case")).toBeInTheDocument();
});

test("renders accommodation type and area for a flight plus hotel brief", () => {
  render(<BriefPanel brief={{ ...baseBrief, search_mode: "flight_hotel", accommodation_type: "home",
    accommodation_area: "Trastevere" }} />);
  expect(screen.getByText("Volo + hotel")).toBeInTheDocument();
  expect(screen.getByText("Case")).toBeInTheDocument();
  expect(screen.getByText("Zona alloggio")).toBeInTheDocument();
  expect(screen.getByText("Trastevere")).toBeInTheDocument();
});

test("does not show accommodation details for a flight-only brief", () => {
  render(<BriefPanel brief={{ ...baseBrief, search_mode: "flight_only", accommodation_type: "home",
    accommodation_area: "Trastevere" }} />);
  expect(screen.queryByText("Zona alloggio")).not.toBeInTheDocument();
  expect(screen.queryByText("Case")).not.toBeInTheDocument();
});

test("null brief shows placeholder destination", () => {
  render(<BriefPanel brief={null} />);
  expect(screen.getByText("Da definire")).toBeInTheDocument();
});

test("flexible dates show window, nights and a flexibility hint", () => {
  render(<BriefPanel brief={{ ...baseBrief, date_from: "2026-08-18", date_to: "2026-08-25",
    window_from: "2026-08-18", window_to: "2026-08-31", trip_nights: 7, dates_flexible: true }} />);
  expect(screen.getByText(/2026-08-18/)).toBeInTheDocument();
  expect(screen.getByText(/2026-08-31/)).toBeInTheDocument();
  expect(screen.getByText(/7 notti/)).toBeInTheDocument();
  expect(screen.getByText(/date esatte secondo l'offerta/i)).toBeInTheDocument();
});

test("fixed dates render the locked date pair unchanged", () => {
  render(<BriefPanel brief={{ ...baseBrief, date_from: "2026-09-01", date_to: "2026-09-08" }} />);
  expect(screen.getByText("2026-09-01 → 2026-09-08")).toBeInTheDocument();
});

test("does not render board (trattamento) or pool (piscina) rows", () => {
  render(<BriefPanel brief={baseBrief} />);
  expect(screen.queryByText("Trattamento")).not.toBeInTheDocument();
  expect(screen.queryByText("Piscina")).not.toBeInTheDocument();
});

test("a malformed (unparsed) budget value never renders a NaN budget row", () => {
  // A custom budget like "900 a persona" that slipped through unparsed used to render
  // "NaN EUR a persona"; the panel must now skip it instead.
  render(<BriefPanel brief={{ ...baseBrief, budget_per_person: "900 a persona" as unknown as number }} />);
  expect(screen.queryByText(/NaN/)).not.toBeInTheDocument();
});
