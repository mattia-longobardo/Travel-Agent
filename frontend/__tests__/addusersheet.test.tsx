import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AddUserSheet } from "@/components/admin/AddUserSheet";
vi.mock("@/lib/api", () => ({ adminCreateUser: vi.fn().mockResolvedValue({}) }));
import * as api from "@/lib/api";

test("creates a user", async () => {
  const onCreated = vi.fn();
  render(<AddUserSheet open onOpenChange={() => {}} onCreated={onCreated} />);
  fireEvent.change(screen.getByPlaceholderText(/nome utente/i), { target: { value: "carl" } });
  fireEvent.change(screen.getByPlaceholderText(/^email/i), { target: { value: "c@x" } });
  fireEvent.change(screen.getByPlaceholderText(/password/i), { target: { value: "pw" } });
  fireEvent.click(screen.getByRole("button", { name: /^aggiungi/i }));
  await waitFor(() => expect(api.adminCreateUser).toHaveBeenCalledWith(
    expect.objectContaining({ username: "carl", email: "c@x", password: "pw" })));
});
