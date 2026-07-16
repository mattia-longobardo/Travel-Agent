import { Suspense } from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import AdminChatDetail from "@/app/admin/analytics/chats/[id]/page";

// Next.js 16 passes route params as a Promise; the page unwraps it with React `use()`.
// Wrapping render in `await act` flushes the suspense resolution so the page mounts.
async function renderDetail() {
  const params = Promise.resolve({ id: "5" });
  await act(async () => {
    render(
      <Suspense fallback={null}>
        <AdminChatDetail params={params} />
      </Suspense>,
    );
  });
}

const router = { push: vi.fn(), replace: vi.fn(), back: vi.fn() };
vi.mock("next/navigation", () => ({
  useRouter: () => router,
  useSearchParams: () => new URLSearchParams("range=7d"),
}));

vi.mock("@/lib/api", () => ({
  me: vi.fn().mockResolvedValue({ id: 1, username: "admin", email: "a@x", is_admin: true }),
  adminChatDetail: vi.fn().mockResolvedValue({
    range: "7d",
    chat: { id: 5, title: "Roma weekend", owner_username: "bob", created_at: "2026-06-19T10:00:00Z" },
    messages: [
      { role: "user", content: "Voglio andare a Roma", created_at: "2026-06-19T10:00:00Z", tool_calls: null },
      { role: "assistant", content: "Ottima scelta!", created_at: "2026-06-19T10:00:05Z", tool_calls: [{ name: "search" }] },
    ],
    runs: [
      { created_at: "2026-06-19T10:00:05Z", node_path: ["intake", "scout"], total_tokens: 120,
        latency_ms: 1800, model: "gpt-x", cost_usd: 0.0012, ok: true, error: null, outcome: "success" },
      { created_at: "2026-06-19T10:00:10Z", node_path: ["intake"], total_tokens: 50,
        latency_ms: 900, model: "gpt-x", cost_usd: null, ok: false, error: "boom", outcome: "error" },
      { created_at: "2026-06-19T10:00:12Z", node_path: ["intake"], total_tokens: 0,
        latency_ms: 100, model: "gpt-x", cost_usd: null, ok: false, error: "stopped_by_user", outcome: "cancelled" },
    ],
    stats: {
      message_count: 2, run_count: 3, total_tokens: 170, avg_latency_ms: 933,
      prompt_tokens: 80, completion_tokens: 40, estimated_cost_usd: 0.0012, has_unpriced: true,
      success_count: 1, error_count: 1, cancelled_count: 1, success_rate: 0.5,
    },
  }),
}));
import * as api from "@/lib/api";

beforeEach(() => {
  vi.clearAllMocks();
});

test("loads detail via the route id and renders the transcript", async () => {
  await renderDetail();
  await waitFor(() => expect(api.adminChatDetail).toHaveBeenCalledWith(5, "7d"));
  // Transcript tab is default: both bubbles visible
  expect(screen.getByText("Voglio andare a Roma")).toBeInTheDocument();
  expect(screen.getByText("Ottima scelta!")).toBeInTheDocument();
  expect(screen.getByText(/messaggi, run e metriche: ultimi 7 giorni/i)).toBeInTheDocument();
  expect(screen.getByText(/proprietario: bob.*chat creata:/i)).toBeInTheDocument();
});

test("the back button restores the previous filtered analytics page", async () => {
  await renderDetail();
  await waitFor(() => expect(screen.getByText("Voglio andare a Roma")).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: "Indietro" }));
  expect(router.back).toHaveBeenCalledOnce();
});

test("switching to the Statistiche tab shows the per-run table", async () => {
  await renderDetail();
  await waitFor(() => expect(screen.getByText("Voglio andare a Roma")).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: /statistiche/i }));
  // KPI + run-table content
  await waitFor(() => expect(screen.getByText("Modello")).toBeInTheDocument());
  expect(screen.getAllByText("gpt-x").length).toBeGreaterThan(0);
  expect(screen.getAllByText("$0.0012").length).toBeGreaterThan(0);
  expect(screen.getByText("Totale parziale: modelli senza tariffa esclusi")).toBeInTheDocument();
  expect(screen.getByText("scout")).toBeInTheDocument();
  expect(screen.getByText("OK")).toBeInTheDocument();
  expect(screen.getByText("Annullato")).toBeInTheDocument();
});

test("shows run error text and expandable tool calls", async () => {
  await renderDetail();
  await waitFor(() => expect(screen.getByText("Voglio andare a Roma")).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: /statistiche/i }));
  expect(await screen.findByText("boom")).toBeInTheDocument();
});
