import { render, screen, waitFor } from "@testing-library/react";
import { StayDetailsClient } from "@/app/stays/[hotelId]/StayDetailsClient";

test("shows property characteristics on an internal information page without booking links", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      id: 7,
      name: "Casa Navona",
      address: "Roma",
      stars: 0,
      check_in_time: "15:00",
      check_out_time: "11:00",
      description: "Appartamento nel centro storico.",
      gallery: ["https://cdn.example/one.jpg"],
      facilities: ["Cucina", "Aria condizionata"],
      policies: { wifi_free: true, parking_available: false, pets_allowed: true },
      location: null,
      total_room_options: 1,
      rooms: [{ name: "Appartamento", meal_plan: "ROOM_ONLY", cancellation: "Cancellazione gratuita" }],
    }),
  }));
  render(
    <StayDetailsClient hotelId="7" query={{
      searchId: "123", dateFrom: "2026-09-01", dateTo: "2026-09-05", kind: "home",
    }} />,
  );
  await waitFor(() => expect(screen.getByRole("heading", { name: "Casa Navona" })).toBeInTheDocument());
  expect(screen.getByText(/appartamento nel centro storico/i)).toBeInTheDocument();
  expect(screen.getByText(/wi-fi gratuito/i)).toBeInTheDocument();
  expect(screen.getByText(/animali ammessi/i)).toBeInTheDocument();
  expect(screen.getByText("Cucina")).toBeInTheDocument();
  const map = screen.getByTitle("Mappa interattiva di Casa Navona");
  expect(map.getAttribute("src")).toContain("https://www.google.com/maps?");
  expect(map.getAttribute("src")).toContain("q=Casa+Navona%2C+Roma");
  expect(map).toHaveAttribute("allowfullscreen");
  expect(screen.getByText(/cercata sulla mappa tramite nome e indirizzo/i)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /apri in google maps/i })).toHaveAttribute(
    "href",
    expect.stringContaining("query=Casa+Navona%2C+Roma"),
  );
  expect(screen.getByRole("link", { name: /indicazioni/i })).toHaveAttribute(
    "href",
    expect.stringContaining("destination=Casa+Navona%2C+Roma"),
  );
  expect(screen.queryByRole("link", { name: /prenota/i })).not.toBeInTheDocument();
  expect(screen.queryByText(/GBP|sterline|£/i)).not.toBeInTheDocument();
  vi.unstubAllGlobals();
});

test("shows an interactive exact-position map and the allowlisted original-provider page", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      id: 336937,
      name: "Hotel Exact",
      address: "Avenida Adeje 300, 12",
      stars: 4,
      description: "Struttura sul mare.",
      gallery: [],
      facilities: ["Piscina", "Wi-Fi"],
      policies: { wifi_free: true },
      location: {
        lat: 28.1221,
        lng: -16.7752,
        label: "Avenida Adeje 300, 12",
        source: "provider",
        confidence: 1,
      },
      original_url: "https://www.it.lastminute.com/hotel/spagna/adeje/hotel-exact_hid-336937",
      total_room_options: 1,
      rooms: [{
        name: "Doppia vista mare",
        meal_plan: "BED_BREAKFAST",
        cancellation: "Cancellazione gratuita",
        deposit_required: false,
        price: 745,
        currency: "EUR",
      }],
    }),
  }));
  render(
    <StayDetailsClient hotelId="336937" query={{
      searchId: "543500301", dateFrom: "2026-09-05", dateTo: "2026-09-12",
      kind: "hotel", facilities: ["Spa"], rating: 87, reviews: 835,
      distanceKm: 1.4, cancellable: true, pricePerPerson: 745, currency: "EUR",
    }} />,
  );

  await waitFor(() => expect(screen.getByRole("heading", { name: "Hotel Exact" })).toBeInTheDocument());
  const map = screen.getByTitle("Mappa interattiva di Hotel Exact");
  expect(map.getAttribute("src")).toContain("https://www.google.com/maps?");
  expect(map.getAttribute("src")).toContain("q=28.1221%2C-16.7752");
  expect(map).toHaveAttribute("referrerpolicy", "no-referrer-when-downgrade");
  expect(screen.getByRole("link", { name: /apri in google maps/i })).toHaveAttribute(
    "href",
    expect.stringContaining("query=28.1221%2C-16.7752"),
  );
  expect(screen.getByRole("link", { name: /indicazioni/i })).toHaveAttribute(
    "href",
    expect.stringContaining("destination=28.1221%2C-16.7752"),
  );
  expect(screen.getByText("Spa")).toBeInTheDocument();
  expect(screen.getByText(/Doppia vista mare/i)).toBeInTheDocument();
  expect(screen.getAllByText(/745/).length).toBeGreaterThan(0);
  const original = screen.getByRole("link", { name: /apri la pagina su lastminute\.com/i });
  expect(original).toHaveAttribute(
    "href",
    "https://www.it.lastminute.com/hotel/spagna/adeje/hotel-exact_hid-336937",
  );
  expect(original.getAttribute("href")).not.toContain("/api/go/hotel");
  vi.unstubAllGlobals();
});

test("does not expose the original-site CTA when the backend returns a sales funnel", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      id: 7,
      name: "Hotel unsafe",
      gallery: [],
      facilities: [],
      policies: {},
      location: null,
      original_url: "https://www.lastminute.com/s/tsx/7?pageType=review&pricingId=SECRET",
      total_room_options: 0,
      rooms: [],
    }),
  }));
  render(
    <StayDetailsClient hotelId="7" query={{
      searchId: "123", dateFrom: "2026-09-01", dateTo: "2026-09-05",
      kind: "hotel",
    }} />,
  );
  await waitFor(() => expect(screen.getByRole("heading", { name: "Hotel unsafe" })).toBeInTheDocument());
  expect(screen.queryByRole("link", { name: /lastminute\.com/i })).not.toBeInTheDocument();
  vi.unstubAllGlobals();
});

test("keeps all search-result details visible when the expired provider session returns 404", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 404 }));

  render(
    <StayDetailsClient hotelId="20344" query={{
      searchId: "518602583",
      dateFrom: "2026-09-09",
      dateTo: "2026-09-15",
      kind: "hotel",
      name: "Dom Pedro Garajau",
      destination: "Santa Cruz, Portogallo",
      image: "https://cdn.example/dom-pedro.jpg",
      stars: 4,
      rating: 8.6,
      reviews: 421,
      facilities: ["Piscina", "Wi-Fi"],
      nights: 6,
      pricePerPerson: 640,
      priceTotal: 1920,
      currency: "EUR",
    }} />,
  );

  await waitFor(() => expect(screen.queryByLabelText("Caricamento dettagli")).not.toBeInTheDocument());
  expect(screen.getByRole("heading", { name: "Dom Pedro Garajau" })).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "Dom Pedro Garajau" })).toHaveAttribute(
    "src",
    "https://cdn.example/dom-pedro.jpg",
  );
  expect(screen.getByLabelText("4 stelle")).toBeInTheDocument();
  expect(screen.getByText(/8,6\/10/)).toBeInTheDocument();
  expect(screen.getByText(/421 recensioni/)).toBeInTheDocument();
  expect(screen.getByText("Piscina")).toBeInTheDocument();
  expect(screen.getByText("Wi-Fi")).toBeInTheDocument();
  expect(screen.getAllByText("Santa Cruz, Portogallo").length).toBeGreaterThan(0);
  expect(screen.getAllByText(/640/).length).toBeGreaterThan(0);
  expect(screen.getByText(/Totale indicativo/)).toHaveTextContent(/1920/);
  expect(screen.queryByText(/non è stato possibile caricare/i)).not.toBeInTheDocument();

  const map = screen.getByTitle("Mappa interattiva di Dom Pedro Garajau");
  expect(map.getAttribute("src")).toContain("q=Dom+Pedro+Garajau%2C+Santa+Cruz%2C+Portogallo");
  vi.unstubAllGlobals();
});

test("merges a partial live payload with query fallbacks and preserves its original URL", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      id: 20344,
      name: null,
      address: null,
      facilities: ["Navetta aeroportuale"],
      original_url: "https://www.it.lastminute.com/hotel/portogallo/santa-cruz/dom-pedro-garajau_hid-20344",
    }),
  }));

  render(
    <StayDetailsClient hotelId="20344" query={{
      searchId: "518602583",
      dateFrom: "2026-09-09",
      dateTo: "2026-09-15",
      kind: "hotel",
      name: "Dom Pedro Garajau",
      destination: "Santa Cruz, Portogallo",
      image: "https://cdn.example/dom-pedro.jpg",
      stars: 4,
      facilities: ["Piscina"],
      pricePerPerson: 640,
      currency: "EUR",
    }} />,
  );

  await waitFor(() => expect(screen.getByText("Navetta aeroportuale")).toBeInTheDocument());
  expect(screen.getByRole("heading", { name: "Dom Pedro Garajau" })).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "Dom Pedro Garajau" })).toHaveAttribute(
    "src",
    "https://cdn.example/dom-pedro.jpg",
  );
  expect(screen.getByLabelText("4 stelle")).toBeInTheDocument();
  expect(screen.getByText("Piscina")).toBeInTheDocument();
  expect(screen.getAllByText(/640/).length).toBeGreaterThan(0);
  expect(screen.getByTitle("Mappa interattiva di Dom Pedro Garajau")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /apri la pagina su lastminute\.com/i })).toHaveAttribute(
    "href",
    "https://www.it.lastminute.com/hotel/portogallo/santa-cruz/dom-pedro-garajau_hid-20344",
  );
  expect(screen.queryByText(/non è stato possibile caricare/i)).not.toBeInTheDocument();
  vi.unstubAllGlobals();
});
