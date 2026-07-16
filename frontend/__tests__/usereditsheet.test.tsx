import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { UserEditSheet } from "@/components/admin/UserEditSheet";
vi.mock("@/lib/api", () => ({
  adminUpdateUser: vi.fn().mockResolvedValue({}),
  adminDeleteUser: vi.fn().mockResolvedValue(undefined),
}));
import * as api from "@/lib/api";

const user = { id: 2, username: "bob", email: "b@x", is_admin: false, is_active: true, group_id: null };

test("saves changed username", async () => {
  const onSaved = vi.fn();
  render(<UserEditSheet user={user} groups={[]} canDelete onClose={() => {}} onSaved={onSaved} />);
  fireEvent.change(screen.getByLabelText(/username/i), { target: { value: "bobby" } });
  fireEvent.click(screen.getByRole("button", { name: /salva/i }));
  await waitFor(() => expect(api.adminUpdateUser).toHaveBeenCalledWith(2,
    expect.objectContaining({ username: "bobby" })));
  await waitFor(() => expect(onSaved).toHaveBeenCalled());
});
