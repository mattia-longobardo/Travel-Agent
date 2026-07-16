import { render, screen } from "@testing-library/react";
import { ModelBreakdownTable } from "@/components/admin/ModelBreakdownTable";

const data = { items: [
  { model: "gpt-5.4", runs: 2, prompt_tokens: 1000, completion_tokens: 500, total_tokens: 1500,
    avg_latency_ms: 300, successes: 2, errors: 0, cancelled: 0, success_rate: 1,
    cost_usd: 0.0105, cost_per_run_usd: 0.00525 },
  { model: "gpt-x", runs: 1, prompt_tokens: 5, completion_tokens: 5, total_tokens: 10,
    avg_latency_ms: 600, successes: 0, errors: 1, cancelled: 0, success_rate: 0,
    cost_usd: null, cost_per_run_usd: null },
], total_cost_usd: 0.0105, has_unpriced: true };

test("renders models, cost and n/d", () => {
  render(<ModelBreakdownTable data={data} />);
  expect(screen.getByText("gpt-5.4")).toBeInTheDocument();
  expect(screen.getAllByText("n/d").length).toBeGreaterThan(0);
  expect(screen.getByText("100.0%")).toBeInTheDocument();
  expect(screen.getByText(/stima/i)).toBeInTheDocument();  // unpriced note
});
