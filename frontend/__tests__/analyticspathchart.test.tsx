import { render, screen } from "@testing-library/react";
import { AnalyticsPathChart } from "@/components/admin/AnalyticsPathChart";

test("empty paths shows empty state", () => {
  render(<AnalyticsPathChart paths={[]} />);
  expect(screen.getByText(/nessun percorso/i)).toBeInTheDocument();
});

test("renders with paths", () => {
  render(<AnalyticsPathChart paths={[{ path: ["intake", "scout"], count: 5, avg_latency_ms: 100, avg_tokens: 20 }]} />);
  expect(screen.getByText("intake")).toBeInTheDocument();
  expect(screen.getByText("scout")).toBeInTheDocument();
  expect(screen.getByTestId("path-row")).toHaveTextContent(/5 run · 100 ms · 20 tok/i);
});
