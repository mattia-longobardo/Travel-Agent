import { fireEvent, render, screen } from "@testing-library/react";
import { TravelModeSelector } from "@/components/TravelModeSelector";

test("mostra il selettore alloggio per Solo hotel e Volo + hotel, ma non per Solo volo", () => {
  const onModeChange = vi.fn();
  const onAccommodationTypeChange = vi.fn();
  const { rerender } = render(
    <TravelModeSelector mode="flight_hotel" accommodationType="both"
      onModeChange={onModeChange} onAccommodationTypeChange={onAccommodationTypeChange} />,
  );
  expect(screen.getAllByRole("tab")).toHaveLength(3);
  expect(screen.getAllByRole("radio")).toHaveLength(3);
  fireEvent.click(screen.getByRole("radio", { name: /^case/i }));
  expect(onAccommodationTypeChange).toHaveBeenCalledWith("home");

  rerender(
    <TravelModeSelector mode="flight_only" accommodationType="both"
      onModeChange={onModeChange} onAccommodationTypeChange={onAccommodationTypeChange} />,
  );
  expect(screen.queryByRole("radiogroup", { name: /tipo di alloggio/i })).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("tab", { name: /solo hotel/i }));
  expect(onModeChange).toHaveBeenCalledWith("hotel_only");

  rerender(
    <TravelModeSelector mode="hotel_only" accommodationType="both"
      onModeChange={onModeChange} onAccommodationTypeChange={onAccommodationTypeChange} />,
  );
  expect(screen.getAllByRole("radio")).toHaveLength(3);
  expect(screen.getByRole("radio", { name: /hotel e case/i })).toHaveAttribute("aria-checked", "true");
});
