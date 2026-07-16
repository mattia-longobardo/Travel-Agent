import { render, screen } from "@testing-library/react";
import { MessageBubble } from "@/components/MessageBubble";

test("rende il contenuto utente come testo semplice", () => {
  render(<MessageBubble role="user" content="Ciao mondo" />);
  expect(screen.getByText("Ciao mondo")).toBeInTheDocument();
});

test("user bubble wraps long content", () => {
  const { container } = render(
    <MessageBubble role="user" content={"x".repeat(200)} />
  );
  // bubble container is the inner div with px-4
  const bubble = container.querySelector(".px-4");
  expect(bubble?.className).toMatch(/break-words/);
});

test("assistant bubble wraps long content", () => {
  const { container } = render(<MessageBubble role="assistant" content={"y".repeat(200)} />);
  const bubble = container.querySelector(".px-4");
  expect(bubble?.className).toMatch(/break-words/);
});
