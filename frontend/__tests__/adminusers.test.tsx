import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AdminUsers from "@/app/admin/users/page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("@/lib/api", () => ({
  me: vi.fn().mockResolvedValue({ id: 1, username: "admin", email: "a@x", is_admin: true }),
  adminListUsers: vi.fn().mockResolvedValue({
    items: [
      { id: 1, username: "admin", email: "a@x", is_admin: true, is_active: true, group_id: null },
      { id: 2, username: "bob", email: "b@x", is_admin: false, is_active: true, group_id: null },
    ], total: 2, page: 1, page_size: 50 }),
  adminUsersStats: vi.fn().mockResolvedValue({ total: 2, active: 2, inactive: 0, admins: 1 }),
  adminListGroups: vi.fn().mockResolvedValue([]),
  adminBulkUsers: vi.fn().mockResolvedValue({ affected: 1, skipped: [] }),
  adminUsersCsvUrl: vi.fn().mockReturnValue("/api/admin/users/export.csv"),
  adminUpdateUser: vi.fn().mockResolvedValue({}),
  adminDeleteUser: vi.fn().mockResolvedValue(undefined),
  adminCreateUser: vi.fn().mockResolvedValue({}),
}));
import * as api from "@/lib/api";

test("renders the table from the paginated envelope", async () => {
  render(<AdminUsers />);
  await waitFor(() => expect(screen.getByText("bob")).toBeInTheDocument());
  expect(screen.getByText("admin")).toBeInTheDocument();
});

test("selecting a user shows the bulk bar and dispatches deactivate", async () => {
  render(<AdminUsers />);
  await waitFor(() => expect(screen.getByText("bob")).toBeInTheDocument());
  fireEvent.click(screen.getByLabelText("Seleziona bob"));
  fireEvent.click(await screen.findByRole("button", { name: /disattiva/i }));
  await waitFor(() => expect(api.adminBulkUsers).toHaveBeenCalledWith(
    expect.objectContaining({ action: "deactivate", user_ids: [2] })));
});

test("opening a row shows the edit drawer", async () => {
  render(<AdminUsers />);
  await waitFor(() => expect(screen.getByText("bob")).toBeInTheDocument());
  fireEvent.click(screen.getByText("bob"));
  await waitFor(() => expect(screen.getByText("Modifica utente")).toBeInTheDocument());
});
