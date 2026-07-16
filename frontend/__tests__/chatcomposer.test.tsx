import { render, screen, fireEvent } from "@testing-library/react";
import { ChatComposer } from "@/components/ChatComposer";

test("renders Stop while sending and calls onStop", () => {
  const onStop = vi.fn();
  render(
    <ChatComposer value="" onChange={() => {}} onSend={() => {}}
      disabled sending onStop={onStop} />,
  );
  const stop = screen.getByLabelText("Interrompi");
  fireEvent.click(stop);
  expect(onStop).toHaveBeenCalled();
  expect(screen.queryByLabelText("Cerca")).toBeNull();
});

test("renders Send when idle", () => {
  render(
    <ChatComposer value="x" onChange={() => {}} onSend={() => {}}
      disabled={false} sending={false} onStop={() => {}} />,
  );
  expect(screen.getByLabelText("Cerca")).toBeTruthy();
  expect(screen.queryByLabelText("Interrompi")).toBeNull();
});
