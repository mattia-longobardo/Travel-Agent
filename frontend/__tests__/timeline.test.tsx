import { render, screen } from "@testing-library/react";
import { AgentTimeline } from "@/components/AgentTimeline";

test("renders latest status per agent", () => {
  render(<AgentTimeline steps={[
    { type: "agent_step", agent: "flight", status: "running", label: "Cerco i voli" },
    { type: "agent_step", agent: "flight", status: "done", label: "Cerco i voli" },
  ]} />);
  expect(screen.getByText("Cerco i voli")).toBeInTheDocument();
  expect(screen.getByTestId("step-flight")).toHaveAttribute("data-status", "done");
});
