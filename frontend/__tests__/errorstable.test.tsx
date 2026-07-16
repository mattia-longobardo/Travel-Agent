import { render, screen } from "@testing-library/react";
import { ErrorsTable } from "@/components/admin/ErrorsTable";

const items = [{ created_at: "2026-06-02T10:00:00Z", chat_id: 9, chat_title: "Roma",
  owner_username: "admin", model: "gpt-x", error: "boom", latency_ms: 600 }];

test("renders error rows with chat link and text", () => {
  render(<ErrorsTable items={items} range="7d" />);
  expect(screen.getByText("boom")).toBeInTheDocument();
  expect(screen.getByRole("columnheader", { name: "Proprietario" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /roma/i })).toHaveAttribute("href", "/admin/analytics/chats/9?range=7d");
});

test("empty state", () => {
  render(<ErrorsTable items={[]} range="7d" />);
  expect(screen.getByText(/nessun errore/i)).toBeInTheDocument();
});
