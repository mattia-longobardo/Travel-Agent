import { render, screen } from "@testing-library/react";
import { PackageCard } from "@/components/PackageCard";

const data = {
  id: "pkg-1",
  kind: "package" as const,
  badge: "best_value" as const,
  destination: "Tenerife (TFS)",
  price_per_person: 690,
  price_total: 1380,
  currency: "EUR",
  nights: 7,
  hotel_name: "Hotel Sol",
  hotel_stars: 4,
  hotel_rating: 8.6,
  flight_summary: "MXP → TFS",
  reason: "7 nights all-inclusive",
  booking_url: "https://x",
};

test("shows price per person and badge label", () => {
  render(<PackageCard data={data} />);
  expect(screen.getByText(/690/)).toBeInTheDocument();
  expect(screen.getByText(/Miglior valore/i)).toBeInTheDocument();
  expect(screen.getByText("Tenerife (TFS)")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /vai all'offerta/i })).toHaveAttribute(
    "href",
    "https://x"
  );
});

test("a long destination title wraps without being clipped", () => {
  render(<PackageCard data={{ ...data, destination: "Creta (Heraklion) (HER)" }} />);
  const title = screen.getByText("Creta (Heraklion) (HER)");
  expect(title.className).toMatch(/break-words/);
  expect(title.className).not.toMatch(/line-clamp/);
  expect(title.className).not.toMatch(/\btruncate\b/);
});

test("never renders a fake href when booking_url is missing", () => {
  render(<PackageCard data={{ ...data, booking_url: null }} />);
  expect(screen.queryByRole("link", { name: /vai all'offerta/i })).not.toBeInTheDocument();
  expect(screen.getByText(/offerta non disponibile/i)).toBeInTheDocument();
});

test("uses the offer's own image when provided", () => {
  render(<PackageCard data={{ ...data, image_url: "https://cdn.example/img.jpg" }} />);
  const img = screen.getByRole("img", { name: "Tenerife (TFS)" });
  expect(img).toHaveAttribute("src", "https://cdn.example/img.jpg");
});

test("flags unmet search parameters and shows the trip dates", () => {
  render(
    <PackageCard
      data={{ ...data, date_from: "2026-08-24", date_to: "2026-08-31", unmet: ["Supera il budget di 120€ a persona"] }}
    />
  );
  expect(screen.getByText(/Supera il budget di 120/)).toBeInTheDocument();
  expect(screen.getByText(/ago/)).toBeInTheDocument();
});

test("shows the departure airport when provided", () => {
  render(<PackageCard data={{ ...data, departure_iata: "MXP" }} />);
  expect(screen.getByText(/da MXP/)).toBeInTheDocument();
});

test("long flight and hotel text wraps instead of being cut", () => {
  const longFlight = "MXP 20:00 → PDL 08:45+1 PDL 16:40 → MXP 19:55 scalo a Lisbona di 4 ore e quaranta con cambio terminal e seconda tratta operata da partner";
  const longHotel = "Grand Hotel Resort & Spa Atlantico Oceanfront Premium All-Inclusive Wellness Retreat Collection";
  render(
    <PackageCard data={{ ...data, hotel_name: longHotel, flight_summary: longFlight, departure_iata: "MXP" }} />
  );
  const flightNode = screen.getByText(new RegExp("da MXP"));
  const hotelNode = screen.getByText(new RegExp(longHotel.slice(0, 20)));
  expect(flightNode.className).toMatch(/break-words/);
  expect(hotelNode.className).toMatch(/break-words/);
  expect(flightNode.className).not.toMatch(/truncate/);
  expect(hotelNode.className).not.toMatch(/truncate/);
  expect(flightNode.parentElement!.className).toMatch(/min-w-0/);
  expect(hotelNode.parentElement!.className).toMatch(/min-w-0/);
});

const separate = {
  id: "sep-1",
  kind: "separate" as const,
  badge: null,
  destination: "Creta (HER)",
  price_per_person: 540,
  price_total: 1080,
  currency: "EUR",
  nights: 7,
  flight_pp: 180,
  hotel_pp: 360,
  flight_url: "https://flight.example/deeplink",
  hotel_url: "https://hotel.example/checkout",
  booking_url: "https://hotel.example/checkout",
};

test("separate card labels the headline price as an estimate (volo + hotel)", () => {
  render(<PackageCard data={separate} />);
  expect(screen.getByText(/stima volo \+ hotel/i)).toBeInTheDocument();
});

test("separate card shows the flight/hotel price breakdown when both present", () => {
  render(<PackageCard data={separate} />);
  expect(screen.getByText(/Volo 180€ · Hotel 360€ a persona/)).toBeInTheDocument();
});

test("separate card renders two CTAs pointing at hotel_url and flight_url", () => {
  render(<PackageCard data={separate} />);
  expect(screen.getByRole("link", { name: /prenota hotel/i })).toHaveAttribute(
    "href",
    "https://hotel.example/checkout"
  );
  expect(screen.getByRole("link", { name: /prenota volo/i })).toHaveAttribute(
    "href",
    "https://flight.example/deeplink"
  );
  expect(screen.queryByRole("link", { name: /vai all'offerta/i })).not.toBeInTheDocument();
});

test("separate card never sends Prenota volo to the hotel booking url", () => {
  render(<PackageCard data={{ ...separate, flight_url: null }} />);
  expect(screen.getByRole("link", { name: /prenota hotel/i })).toHaveAttribute(
    "href",
    "https://hotel.example/checkout"
  );
  expect(screen.queryByRole("link", { name: /prenota volo/i })).not.toBeInTheDocument();
  expect(screen.getByText(/volo non disponibile/i)).toBeInTheDocument();
});

test("separate card with no hotel/flight urls falls back to a single CTA on booking_url", () => {
  render(<PackageCard data={{ ...separate, flight_url: null, hotel_url: null }} />);
  expect(screen.getByRole("link", { name: /vai all'offerta/i })).toHaveAttribute(
    "href",
    "https://hotel.example/checkout"
  );
  expect(screen.queryByRole("link", { name: /prenota hotel/i })).not.toBeInTheDocument();
});

test("separate card rejects a non-http(s) booking link scheme", () => {
  render(
    <PackageCard
      data={{ ...separate, flight_url: "javascript:alert(1)", hotel_url: "javascript:alert(1)", booking_url: "javascript:alert(1)" }}
    />
  );
  expect(screen.queryByRole("link", { name: /vai all'offerta/i })).not.toBeInTheDocument();
  expect(screen.getByText(/offerta non disponibile/i)).toBeInTheDocument();
  expect(document.querySelector('a[href^="javascript:"]')).not.toBeInTheDocument();
});

test("package card keeps a single 'Vai all'offerta' CTA", () => {
  render(<PackageCard data={data} />);
  expect(screen.getByRole("link", { name: /vai all'offerta/i })).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: /prenota hotel/i })).not.toBeInTheDocument();
  expect(screen.queryByText(/stima volo \+ hotel/i)).not.toBeInTheDocument();
});

// --- "Vedi hotel" must open the hotel page, never the checkout/booking page -------------------

test("'Vedi Hotel' opens the internal property page directly when present", () => {
  const presentation = "/stays/123?search_id=9&date_from=2026-08-01&date_to=2026-08-08&kind=hotel";
  render(<PackageCard data={{ ...data, property_url: presentation }} />);
  const href = screen.getByRole("link", { name: /vedi hotel/i }).getAttribute("href") || "";
  expect(href).toMatch(/^\/stays\/123\?/);
  const parsed = new URL(href, "https://travel.test");
  expect(parsed.searchParams.get("search_id")).toBe("9");
  expect(parsed.searchParams.get("name")).toBe("Hotel Sol");
  expect(parsed.searchParams.get("price_per_person")).toBe("690");
});

test("'Vedi Hotel' passes rich card features but never the sales URL to the detail page", () => {
  const presentation = "/stays/336937?search_id=543500301&date_from=2026-09-05&date_to=2026-09-12&kind=hotel";
  const review = "https://www.it.lastminute.com/s/tsx/336937?pageType=review&vcSearchId=543500301";
  render(<PackageCard data={{
    ...data,
    property_url: presentation,
    review_url: review,
    hotel_reviews: 835,
    hotel_distance_km: 1.4,
    hotel_facilities: ["Piscina", "Wi-Fi"],
    hotel_cancellable: false,
  }} />);
  const href = screen.getByRole("link", { name: /vedi hotel/i }).getAttribute("href") || "";
  const parsed = new URL(href, "https://travel.test");
  expect(parsed.searchParams.get("provider_url")).toBeNull();
  expect(parsed.searchParams.get("reviews")).toBe("835");
  expect(parsed.searchParams.get("distance_km")).toBe("1.4");
  expect(JSON.parse(parsed.searchParams.get("facilities") || "[]")).toEqual(["Piscina", "Wi-Fi"]);
  expect(parsed.searchParams.get("cancellable")).toBe("0");
});

test("legacy review property_url is used only to recover the internal property identity", () => {
  const review = "https://www.lastminute.com/s/tsx/336937?pageType=review&vcSearchId=543500301&dateFrom=2026-09-05&dateTo=2026-09-12";
  render(<PackageCard data={{ ...data, property_url: review, review_url: null }} />);
  const href = screen.getByRole("link", { name: /vedi hotel/i }).getAttribute("href") || "";
  const parsed = new URL(href, "https://travel.test");
  expect(parsed.pathname).toBe("/stays/336937");
  expect(parsed.searchParams.get("provider_url")).toBeNull();
});

test("'Vedi hotel' never falls back to the checkout/booking link (package card)", () => {
  // No review_url and no hotel_url: only a minted checkout URL exists. "Vedi hotel" must NOT
  // route there — the user would land on the booking page instead of the hotel page.
  render(<PackageCard data={{ ...data, review_url: null, booking_url: "https://www.lastminute.com/booking/checkout-xyz" }} />);
  expect(screen.getByRole("link", { name: /vedi hotel/i }).getAttribute("href")).not.toContain("checkout-xyz");
});

test("'Vedi hotel' never falls back to the hotel checkout link (separate card)", () => {
  // separate cards carry hotel_url = minted hotel CHECKOUT. "Vedi hotel" must not use it.
  render(<PackageCard data={{ ...separate, review_url: null }} />);
  expect(screen.getByRole("link", { name: /vedi hotel/i }).getAttribute("href")).not.toContain("checkout");
});

test("'Vedi Hotel' defensively rejects a checkout accidentally supplied as property_url", () => {
  render(<PackageCard data={{ ...data, property_url: "https://www.lastminute.com/booking/checkout-xyz" }} />);
  expect(screen.getByRole("link", { name: /vedi hotel/i }).getAttribute("href")).not.toContain("checkout-xyz");
});

test("cards grow with rich content instead of clipping it to a fixed height", () => {
  const minimal = {
    id: "min",
    kind: "separate" as const,
    badge: null,
    destination: "Creta",
    price_per_person: 420,
    price_total: 840,
    currency: "EUR",
    nights: 5,
  };
  const rich = {
    ...data,
    date_from: "2026-08-24",
    date_to: "2026-08-31",
    departure_iata: "MXP",
    flight_summary: "MXP → TFS",
    unmet: ["Supera il budget di 120€ a persona"],
    reason: "Una motivazione molto lunga che descrive in dettaglio perché questo pacchetto è ottimo e dovrebbe andare a capo più volte.",
  };
  const { container } = render(<PackageCard data={minimal} />);
  const card = container.querySelector("[data-slot='card']") ?? container.firstElementChild!;
  expect(card.className).not.toMatch(/h-\[/);

  render(<PackageCard data={rich} />);
  const warning = screen.getByText(/Supera il budget/);
  const reason = screen.getByText(/Una motivazione molto lunga/);
  expect(warning.className).not.toMatch(/line-clamp|truncate/);
  expect(reason.className).not.toMatch(/line-clamp|truncate/);
});

test("flight-only card: no hotel row, flight CTA, no Vedi hotel link", () => {
  render(
    <PackageCard
      data={{
        ...data,
        kind: "flight_only" as const,
        badge: null,
        hotel_name: undefined,
        hotel_stars: undefined,
        hotel_rating: undefined,
        flight_summary: "MXP → ATH 06:00",
        booking_url: "https://lm/volo",
      }}
    />
  );
  expect(screen.getByText(/solo volo/i)).toBeInTheDocument();
  expect(screen.queryByText(/hotel selezionato/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/vedi hotel/i)).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: /prenota volo/i })).toHaveAttribute(
    "href",
    "https://lm/volo"
  );
  expect(screen.getByText(/andata e ritorno/i)).toBeInTheDocument();
});

test("hotel-only card: no flight row, hotel CTA", () => {
  render(
    <PackageCard
      data={{
        ...data,
        kind: "hotel_only" as const,
        badge: null,
        flight_summary: "",
        booking_url: "https://lm/hotel",
      }}
    />
  );
  expect(screen.getByText(/solo hotel/i)).toBeInTheDocument();
  expect(screen.queryByText(/volo incluso/i)).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: /prenota hotel/i })).toHaveAttribute(
    "href",
    "https://lm/hotel"
  );
  expect(screen.getByText(/vedi hotel/i)).toBeInTheDocument();
});

test("short-term rental card uses Casa labels and a prominent detail CTA", () => {
  render(<PackageCard data={{ ...data, kind: "hotel_only", accommodation_kind: "home",
    property_url: "https://www.lastminute.com/s/tsx/house-7", booking_url: "https://www.lastminute.com/checkout/house-7" }} />);
  const detail = screen.getByRole("link", { name: /vedi casa/i });
  expect(detail.getAttribute("href")).toMatch(/^\/stays\/overview\?/);
  expect(detail.getAttribute("href")).toContain("kind=home");
  expect(detail.className).toMatch(/min-h-11/);
  expect(screen.getByRole("link", { name: /prenota casa/i })).toBeInTheDocument();
});

test("historical home card hides stale star warnings and never labels the stay as hotel", () => {
  render(<PackageCard data={{
    ...separate,
    accommodation_kind: "home",
    hotel_name: "Casa Navona",
    unmet: ["Hotel ?★, sotto le 4★ richieste", "Supera il budget di 100€ a persona"],
  }} />);
  expect(screen.getByText(/stima volo \+ casa/i)).toBeInTheDocument();
  expect(screen.getByText(/Volo 180€ · Casa 360€/i)).toBeInTheDocument();
  expect(screen.getByText(/Supera il budget di 100/i)).toBeInTheDocument();
  expect(screen.queryByText(/sotto le 4/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/hotel/i)).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: /prenota casa/i })).toBeInTheDocument();
});

test("package card renders both departure and arrival times from the exact package summary", () => {
  render(<PackageCard data={{
    ...data,
    flight_summary: "A: MXP 05/09 17:25 → TFS 05/09 21:05 · R: TFS 12/09 21:50 → MXP 13/09 03:05",
  }} />);
  expect(screen.getByText(/17:25.*21:05.*21:50.*03:05/)).toBeInTheDocument();
});

test("package card states explicitly when package times are unavailable", () => {
  render(<PackageCard data={{ ...data, flight_summary: "Orari non disponibili · Compagnia EasyJet" }} />);
  expect(screen.getByText(/orari non disponibili.*EasyJet/i)).toBeInTheDocument();
});
