import { render, screen, fireEvent } from "@testing-library/react";
import { ConfirmDialog } from "@/components/admin/ConfirmDialog";

test("calls onConfirm when confirmed", () => {
  const onConfirm = vi.fn();
  render(<ConfirmDialog open title="Eliminare 3 utenti?" confirmLabel="Elimina"
    destructive onConfirm={onConfirm} onOpenChange={() => {}} />);
  fireEvent.click(screen.getByRole("button", { name: /elimina/i }));
  expect(onConfirm).toHaveBeenCalled();
});
