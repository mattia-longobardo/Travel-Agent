import { render, screen, fireEvent } from "@testing-library/react";
import { TimeRangeSelector } from "@/components/admin/TimeRangeSelector";

test("emits the selected range", () => {
  const onChange = vi.fn();
  render(<TimeRangeSelector value="30d" onChange={onChange} />);
  fireEvent.click(screen.getByRole("button", { name: "7g" }));
  expect(onChange).toHaveBeenCalledWith("7d");
});
