import { render, screen } from "@testing-library/react";
vi.mock("recharts", () => {
  const P = ({ children }: { children?: React.ReactNode }) => <div>{children}</div>;
  return { ResponsiveContainer: P, BarChart: P, Bar: () => null,
    XAxis: () => null, YAxis: () => null, Tooltip: () => null, Legend: () => null, CartesianGrid: () => null };
});
import { AnalyticsTimeChart } from "@/components/admin/AnalyticsTimeChart";

test("renders empty state with no data", () => {
  render(<AnalyticsTimeChart data={[]} />);
  expect(screen.getByText(/nessun dato/i)).toBeInTheDocument();
});

test("renders the chart container with data", () => {
  render(<AnalyticsTimeChart data={[{ day: "2026-06-01", runs: 3, successes: 1, errors: 1, cancelled: 1,
    tokens: 100, avg_latency_ms: 300, estimated_cost_usd: 0.01, has_unpriced: false }]} />);
  expect(screen.queryByText(/nessun dato/i)).not.toBeInTheDocument();
  expect(screen.getByLabelText(/esiti dei run/i)).toBeInTheDocument();
});
