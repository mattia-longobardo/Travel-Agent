import { render, screen } from "@testing-library/react";

vi.mock("recharts", () => {
  const P = ({ children }: { children?: React.ReactNode }) => <div>{children}</div>;
  return { ResponsiveContainer: P, BarChart: P, Bar: () => null, XAxis: () => null,
    YAxis: () => null, Tooltip: () => null, CartesianGrid: () => null };
});

import { AnalyticsCostChart } from "@/components/admin/AnalyticsCostChart";

test("renders an empty state without daily costs", () => {
  render(<AnalyticsCostChart data={[]} />);
  expect(screen.getByText(/nessun dato/i)).toBeInTheDocument();
});

test("renders the daily cost chart", () => {
  render(<AnalyticsCostChart data={[{ day: "2026-06-01", runs: 2, successes: 2, errors: 0,
    cancelled: 0, tokens: 120, avg_latency_ms: 300, estimated_cost_usd: 0.004, has_unpriced: true }]} />);
  expect(screen.getByLabelText(/costo stimato per giorno/i)).toBeInTheDocument();
});
