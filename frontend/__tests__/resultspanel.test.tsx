import { fireEvent, render, screen } from "@testing-library/react";
import { ResultsPanel } from "@/components/ResultsPanel";
import type { PackageCardData, ResultBatch } from "@/lib/types";

function packageItem(id: string, kind: PackageCardData["kind"]): PackageCardData {
  return {
    id,
    kind,
    badge: null,
    destination: `Destinazione ${id}`,
    price_per_person: 500,
    price_total: 1000,
    currency: "EUR",
    nights: 5,
  };
}

test("desktop results panel exposes and changes persisted result batches", () => {
  const first = packageItem("prima", "flight_only");
  const latest = packageItem("ultima", "hotel_only");
  const batches: ResultBatch[] = [
    { id: "message-1", packages: [first] },
    { id: "message-2", packages: [latest] },
  ];
  const onSelectResultBatch = vi.fn();

  render(
    <ResultsPanel
      packages={[latest]}
      groups={[]}
      selectedLocation={null}
      onSelectLocation={() => {}}
      resultBatches={batches}
      selectedResultBatchId="message-2"
      onSelectResultBatch={onSelectResultBatch}
    />
  );

  const selector = screen.getByRole("combobox", { name: /ricerca precedente/i });
  expect(selector).toHaveValue("message-2");
  expect(screen.getByRole("option", { name: /ricerca 1 · voli/i })).toBeInTheDocument();
  expect(screen.getByRole("option", { name: /ricerca 2 · alloggi/i })).toBeInTheDocument();
  fireEvent.change(selector, { target: { value: "message-1" } });
  expect(onSelectResultBatch).toHaveBeenCalledWith("message-1");
});

test("desktop historical mini-card labels homes as Casa and filters stale star warnings", () => {
  const home: PackageCardData = {
    ...packageItem("casa", "hotel_only"),
    accommodation_kind: "home",
    unmet: ["Hotel ?★, sotto le 4★ richieste", "Supera il budget di 80€ a persona"],
  };
  render(
    <ResultsPanel
      packages={[home]}
      groups={[]}
      selectedLocation={null}
      onSelectLocation={() => {}}
      searchMode="hotel_only"
      resultBatches={[{ id: "old", packages: [home] }]}
      selectedResultBatchId="old"
      onSelectResultBatch={() => {}}
    />
  );
  expect(screen.getByText(/solo casa/i)).toBeInTheDocument();
  expect(screen.getByText("Casa selezionata")).toBeInTheDocument();
  expect(screen.getByText(/Supera il budget di 80/i)).toBeInTheDocument();
  expect(screen.queryByText(/sotto le 4/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/hotel/i)).not.toBeInTheDocument();
});
