import { render, screen, fireEvent } from "@testing-library/react";
import { MobileTabBar } from "@/components/mobile/MobileTabBar";

test("evidenzia il tab attivo e notifica i cambi", () => {
  const onTab = vi.fn();
  render(<MobileTabBar active="chat" onTab={onTab} resultCount={7} />);
  const chat = screen.getByRole("tab", { name: /pianifica/i });
  expect(chat).toHaveAttribute("aria-selected", "true");
  expect(screen.getByText("7")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", { name: /riepilogo/i }));
  expect(onTab).toHaveBeenCalledWith("brief");
  expect(screen.queryByRole("button", { name: /menu/i })).not.toBeInTheDocument();
});
