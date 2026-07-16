import { render, screen } from "@testing-library/react";
import { MobilePackageCard } from "@/components/mobile/MobilePackageCard";
import type { PackageCardData } from "@/lib/types";

const rental: PackageCardData = {
  id: "home-1", kind: "hotel_only", badge: null, destination: "Roma",
  price_per_person: 240, price_total: 480, currency: "EUR", nights: 3,
  hotel_name: "Casa Navona", accommodation_kind: "home",
  booking_url: "https://www.lastminute.com/checkout/home-1",
  property_url: "https://www.lastminute.com/s/tsx/home-1?pageType=review",
};

test("mobile mostra Vedi Casa separato dal checkout con target touch ampio", () => {
  render(<MobilePackageCard data={rental} />);
  expect(screen.getByRole("link", { name: /prenota casa/i })).toHaveAttribute("href", rental.booking_url);
  const detail = screen.getByRole("link", { name: /vedi casa/i });
  expect(detail.getAttribute("href")).toMatch(/^\/stays\/overview\?/);
  expect(detail.getAttribute("href")).not.toContain("checkout");
  expect(detail.className).toMatch(/min-h-11/);
});

test("mobile filtra il vecchio warning stelle e usa solo etichette Casa", () => {
  render(<MobilePackageCard data={{
    ...rental,
    kind: "package",
    flight_summary: "MXP 10:00 → FCO 11:10",
    unmet: ["Hotel ?★, sotto le 4★ richieste", "Supera il budget di 50€ a persona"],
  }} />);
  expect(screen.getByText(/volo \+ casa/i)).toBeInTheDocument();
  expect(screen.getByText(/Supera il budget di 50/i)).toBeInTheDocument();
  expect(screen.queryByText(/sotto le 4/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/hotel/i)).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: /vedi casa/i })).toBeInTheDocument();
});
