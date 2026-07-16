import { render, screen, fireEvent } from "@testing-library/react";
import { BulkActionBar } from "@/components/admin/BulkActionBar";

test("dispatches bulk actions and select-all", () => {
  const onAction = vi.fn(), onSelectAll = vi.fn();
  render(<BulkActionBar count={5} total={1247} allMatching={false} groups={[]}
    onSelectAllMatching={onSelectAll} onAction={onAction} onClear={() => {}} />);
  fireEvent.click(screen.getByRole("button", { name: /seleziona tutti i 1247/i }));
  expect(onSelectAll).toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: /disattiva/i }));
  expect(onAction).toHaveBeenCalledWith("deactivate");
});
