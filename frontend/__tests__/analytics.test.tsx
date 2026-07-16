import { render, screen, fireEvent, waitFor } from "@testing-library/react";
const push = vi.fn();
const replace = vi.fn();
const router = { push, replace };
vi.mock("next/navigation", () => ({ useRouter: () => router }));
vi.mock("recharts", () => {
  const P = ({ children }: { children?: React.ReactNode }) => <div>{children}</div>;
  return { ResponsiveContainer: P, BarChart: P, Bar: () => null,
    XAxis: () => null, YAxis: () => null, Tooltip: () => null, Legend: () => null, CartesianGrid: () => null };
});
vi.mock("@/lib/api", () => ({
  me: vi.fn().mockResolvedValue({ id: 1, is_admin: true }),
  adminOverview: vi.fn().mockResolvedValue({ total_chats: 2, total_users: 2, total_messages: 2, total_runs: 3,
    total_prompt_tokens: 35, total_completion_tokens: 15, total_tokens: 50, avg_latency_ms: 400, error_rate: 0.33,
    total_successes: 2, total_errors: 1, total_cancelled: 0, success_rate: 0.67,
    estimated_cost_usd: 0, has_unpriced: false, by_day: [] }),
  adminPaths: vi.fn().mockResolvedValue({ paths: [] }),
  adminModels: vi.fn().mockResolvedValue({ items: [], total_cost_usd: 0, has_unpriced: false }),
  adminChats: vi.fn().mockResolvedValue({ items: [
    { chat_id: 7, title: "Tenerife", owner_id: 2, owner_username: "bob", created_at: "2026-06-01T10:00:00Z",
      last_message_at: null, message_count: 2, run_count: 2, total_tokens: 40, avg_latency_ms: 300,
      estimated_cost_usd: 0.0008, has_unpriced: false, success_count: 2, error_count: 0,
      cancelled_count: 0, success_rate: 1 }], total: 1, page: 1, page_size: 50 }),
  adminAnalyticsOwners: vi.fn().mockResolvedValue([{ id: 2, username: "bob" }]),
  adminChatsCsvUrl: vi.fn().mockReturnValue("/api/admin/analytics/chats/export.csv"),
}));
import * as api from "@/lib/api";
import AdminAnalytics from "@/app/admin/analytics/page";

beforeEach(() => {
  vi.clearAllMocks();
});

test("renders KPIs and chats from the new APIs", async () => {
  render(<AdminAnalytics />);
  await waitFor(() => expect(screen.getByText("Tenerife")).toBeInTheDocument());
  expect(screen.getByText("Costo stimato")).toBeInTheDocument();
  expect(screen.getByText("Chat create o attive")).toBeInTheDocument();
  expect(screen.getByText(/click sui risultati e prenotazioni completate non sono ancora tracciati/i)).toBeInTheDocument();
});

test("changing range refetches overview", async () => {
  render(<AdminAnalytics />);
  await waitFor(() => expect(screen.getByText("Tenerife")).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: "7g" }));
  await waitFor(() => expect(api.adminOverview).toHaveBeenCalledWith("7d", undefined));
});

test("the global owner filter refreshes every dataset and CSV", async () => {
  render(<AdminAnalytics />);
  await waitFor(() => expect(screen.getByText("Tenerife")).toBeInTheDocument());
  fireEvent.change(screen.getByLabelText("Proprietario chat"), { target: { value: "2" } });
  await waitFor(() => expect(api.adminOverview).toHaveBeenCalledWith("30d", 2));
  expect(api.adminPaths).toHaveBeenCalledWith("30d", 2);
  expect(api.adminModels).toHaveBeenCalledWith("30d", 2);
  expect(api.adminChats).toHaveBeenCalledWith(expect.objectContaining({ user_id: 2, range: "30d", page: 1 }));
  expect(api.adminChatsCsvUrl).toHaveBeenCalledWith(expect.objectContaining({ user_id: 2, range: "30d" }));
});

test("the errors drill-down keeps period and owner filters", async () => {
  render(<AdminAnalytics />);
  await waitFor(() => expect(screen.getByText("Tenerife")).toBeInTheDocument());
  fireEvent.change(screen.getByLabelText("Proprietario chat"), { target: { value: "2" } });
  fireEvent.click(screen.getByRole("button", { name: /dettaglio errori/i }));
  expect(push).toHaveBeenCalledWith("/admin/analytics/errors?range=30d&user_id=2");
});

test("shows a retry state when loading metrics fails", async () => {
  vi.mocked(api.adminOverview).mockRejectedValueOnce(new Error("offline"));
  render(<AdminAnalytics />);
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent(/metriche non sono disponibili/i);
  fireEvent.click(screen.getByRole("button", { name: /riprova/i }));
  await waitFor(() => expect(api.adminOverview).toHaveBeenCalledTimes(2));
});

test("a failed filter refresh never leaves data from the previous filter visible", async () => {
  render(<AdminAnalytics />);
  await waitFor(() => expect(screen.getByText("Tenerife")).toBeInTheDocument());
  vi.mocked(api.adminOverview).mockRejectedValueOnce(new Error("offline"));
  vi.mocked(api.adminChats).mockRejectedValueOnce(new Error("offline"));
  fireEvent.change(screen.getByLabelText("Proprietario chat"), { target: { value: "2" } });
  await waitFor(() => expect(screen.getAllByRole("alert").length).toBeGreaterThanOrEqual(2));
  expect(screen.queryByText("Tenerife")).not.toBeInTheDocument();
});
