import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SettingsPage from "@/app/settings/page";
const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/lib/api", () => ({
  me: vi.fn().mockResolvedValue({ id: 1, username: "bob", email: "b@x", is_admin: false }),
  updateMe: vi.fn().mockResolvedValue({ id: 1, username: "bobby", email: "b@x", is_admin: false }),
}));
import * as api from "@/lib/api";

test("renders both profile and password sections", async () => {
  render(<SettingsPage />);
  await waitFor(() => expect((screen.getByLabelText(/nome visualizzato/i) as HTMLInputElement).value).toBe("bob"));
  expect(screen.getByRole("button", { name: "Salva profilo" })).toBeInTheDocument();
  expect(screen.getByLabelText(/password attuale/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/nuova password/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Cambia password" })).toBeInTheDocument();
});

test("back button navigates home", async () => {
  push.mockClear();
  render(<SettingsPage />);
  fireEvent.click(screen.getByRole("button", { name: /indietro/i }));
  expect(push).toHaveBeenCalledWith("/");
});

test("loads profile and saves display name", async () => {
  render(<SettingsPage />);
  await waitFor(() => expect((screen.getByLabelText(/nome visualizzato/i) as HTMLInputElement).value).toBe("bob"));
  fireEvent.change(screen.getByLabelText(/nome visualizzato/i), { target: { value: "bobby" } });
  fireEvent.click(screen.getByText("Salva profilo"));
  await waitFor(() => expect(api.updateMe).toHaveBeenCalledWith(expect.objectContaining({ username: "bobby", email: "b@x" })));
});
