import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { UsersToolbar } from "@/components/admin/UsersToolbar";

test("debounced search calls onFilters", async () => {
  const onFilters = vi.fn();
  render(<UsersToolbar filters={{}} groups={[]} pageSize={50}
    onFilters={onFilters} onPageSize={() => {}} />);
  fireEvent.change(screen.getByPlaceholderText(/cerca/i), { target: { value: "bob" } });
  await waitFor(() => expect(onFilters).toHaveBeenCalledWith(
    expect.objectContaining({ q: "bob" })), { timeout: 1000 });
});

test("status filter calls onFilters immediately", () => {
  const onFilters = vi.fn();
  render(<UsersToolbar filters={{}} groups={[]} pageSize={50}
    onFilters={onFilters} onPageSize={() => {}} />);
  fireEvent.change(screen.getByLabelText(/stato/i), { target: { value: "active" } });
  expect(onFilters).toHaveBeenCalledWith(expect.objectContaining({ status: "active" }));
});

test("debounced search uses the latest filters, not a stale closure", async () => {
  const onFilters = vi.fn();
  const { rerender } = render(<UsersToolbar filters={{}} groups={[]} pageSize={50}
    onFilters={onFilters} onPageSize={() => {}} />);
  fireEvent.change(screen.getByPlaceholderText(/cerca/i), { target: { value: "bob" } });
  // parent applies a status filter while the debounce timer is pending
  rerender(<UsersToolbar filters={{ status: "active" }} groups={[]} pageSize={50}
    onFilters={onFilters} onPageSize={() => {}} />);
  await waitFor(() => expect(onFilters).toHaveBeenCalledWith(
    expect.objectContaining({ status: "active", q: "bob" })), { timeout: 1000 });
});
