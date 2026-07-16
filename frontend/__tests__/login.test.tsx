import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import LoginPage from "@/app/login/page";
import * as auth from "@/lib/auth";
import { vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

test("submits email and password", async () => {
  const spy = vi.spyOn(auth, "login").mockResolvedValue(true);
  render(<LoginPage />);
  fireEvent.change(screen.getByPlaceholderText(/email/i), { target: { value: "b@x" } });
  fireEvent.change(screen.getByPlaceholderText(/password/i), { target: { value: "x" } });
  fireEvent.click(screen.getByRole("button", { name: /accedi/i }));
  await waitFor(() => expect(spy).toHaveBeenCalledWith("b@x", "x"));
});
