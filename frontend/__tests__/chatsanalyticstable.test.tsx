import { render, screen, fireEvent } from "@testing-library/react";
import { ChatsAnalyticsTable } from "@/components/admin/ChatsAnalyticsTable";

const rows = [{ chat_id: 7, title: "Tenerife", owner_id: 2, owner_username: "bob",
  created_at: "2026-06-01T10:00:00Z", last_message_at: "2026-06-02T10:00:00Z",
  message_count: 2, run_count: 2, total_tokens: 40, avg_latency_ms: 300,
  estimated_cost_usd: 0.0008, has_unpriced: false, success_count: 2, error_count: 0,
  cancelled_count: 0, success_rate: 1 }];

test("renders rows, sort header and open link", () => {
  const onSort = vi.fn();
  render(<ChatsAnalyticsTable rows={rows} range="30d" sort="created_at" order="desc" onSort={onSort} />);
  expect(screen.getByText("Tenerife")).toBeInTheDocument();
  expect(screen.getByRole("columnheader", { name: "Proprietario" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /token/i }));
  expect(onSort).toHaveBeenCalledWith("total_tokens");
  fireEvent.click(screen.getByRole("button", { name: /costo/i }));
  expect(onSort).toHaveBeenCalledWith("estimated_cost_usd");
  expect(screen.getByText("$0.0008")).toBeInTheDocument();
  expect(screen.getByText("Completata")).toBeInTheDocument();
  expect(screen.getByText(/100%.*0 err.*0 ann/i)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /apri/i })).toHaveAttribute("href", "/admin/analytics/chats/7?range=30d");
});
