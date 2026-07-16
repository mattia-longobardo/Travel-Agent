import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";

const router = { push: vi.fn(), replace: vi.fn(), back: vi.fn() };
vi.mock("next/navigation", () => ({
  useRouter: () => router,
  useSearchParams: () => new URLSearchParams("range=7d&user_id=2&model=gpt-x"),
}));
vi.mock("@/lib/api", () => ({
  me: vi.fn(),
  adminErrors: vi.fn(),
  adminModels: vi.fn(),
}));

import * as api from "@/lib/api";
import type { ErrorsResult, ModelsResult } from "@/lib/types";
import AdminErrors from "@/app/admin/analytics/errors/page";

const errorResult = (title: string, error = "boom"): ErrorsResult => ({
  items: [{ created_at: "2026-06-02T10:00:00Z", chat_id: 9, chat_title: title,
    owner_username: "admin", model: "gpt-x", error, latency_ms: 600 }],
  total: 1, page: 1, page_size: 50,
});

const modelsResult = (model: string): ModelsResult => ({
  items: [{ model, runs: 1, prompt_tokens: 5, completion_tokens: 5, total_tokens: 10,
    avg_latency_ms: 600, successes: 0, errors: 1, cancelled: 0, success_rate: 0,
    cost_usd: null, cost_per_run_usd: null }],
  total_cost_usd: 0,
  has_unpriced: true,
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.me).mockResolvedValue({ id: 1, username: "admin", email: "a@x", is_admin: true });
  vi.mocked(api.adminErrors).mockResolvedValue(errorResult("Roma"));
  vi.mocked(api.adminModels).mockResolvedValue(modelsResult("gpt-x"));
});

test("lists errors and preserves range, owner and model filters", async () => {
  render(<AdminErrors />);
  await waitFor(() => expect(screen.getByText("boom")).toBeInTheDocument());
  expect(api.adminModels).toHaveBeenCalledWith("7d", 2);
  expect(api.adminErrors).toHaveBeenCalledWith(expect.objectContaining({ range: "7d", user_id: 2, model: "gpt-x" }));
  expect(screen.getByRole("link", { name: "Roma" })).toHaveAttribute("href", "/admin/analytics/chats/9?range=7d");
});

test("the back button restores the filtered dashboard", async () => {
  render(<AdminErrors />);
  await waitFor(() => expect(screen.getByText("boom")).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: "Indietro" }));
  expect(router.back).toHaveBeenCalledOnce();
});

test("model and error failures have independent retry states", async () => {
  vi.mocked(api.adminModels).mockRejectedValueOnce(new Error("models offline"));
  vi.mocked(api.adminErrors).mockRejectedValueOnce(new Error("errors offline"));
  render(<AdminErrors />);

  await waitFor(() => expect(screen.getAllByRole("alert")).toHaveLength(2));
  expect(screen.getByText(/caricare i filtri dei modelli/i)).toBeInTheDocument();
  expect(screen.getByText(/caricare gli errori tecnici/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /riprova modelli/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /riprova errori/i })).toBeInTheDocument();
});

test("late responses from the previous range cannot restore stale rows or models", async () => {
  const oldErrors = deferred<ErrorsResult>();
  const oldModels = deferred<ModelsResult>();
  vi.mocked(api.adminErrors).mockImplementation((query) => (
    query?.range === "7d" ? oldErrors.promise : Promise.resolve(errorResult("Nuovo", "new-error"))
  ));
  vi.mocked(api.adminModels).mockImplementation((range) => (
    range === "7d" ? oldModels.promise : Promise.resolve(modelsResult("gpt-new"))
  ));

  render(<AdminErrors />);
  await waitFor(() => expect(api.adminErrors).toHaveBeenCalledWith(expect.objectContaining({ range: "7d" })));
  fireEvent.click(screen.getByRole("button", { name: "30g" }));

  await waitFor(() => expect(screen.getByText("new-error")).toBeInTheDocument());
  expect(screen.getByRole("option", { name: "gpt-new" })).toBeInTheDocument();

  await act(async () => {
    oldErrors.resolve(errorResult("Vecchio", "old-error"));
    oldModels.resolve(modelsResult("gpt-old"));
    await Promise.resolve();
  });

  expect(screen.queryByText("old-error")).not.toBeInTheDocument();
  expect(screen.queryByRole("option", { name: "gpt-old" })).not.toBeInTheDocument();
  expect(screen.getByText("new-error")).toBeInTheDocument();
  expect(screen.getByRole("option", { name: "gpt-new" })).toBeInTheDocument();
});
