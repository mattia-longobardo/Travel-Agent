import { render, screen, fireEvent } from "@testing-library/react";
import { QuestionChips } from "@/components/QuestionChips";
import { vi } from "vitest";

test("calls onAnswer with option value", () => {
  const onAnswer = vi.fn();
  render(<QuestionChips q={{ type: "question", id: "budget_per_person", text: "Budget?",
    options: [{ label: "≤ 750 €", value: 750 }], allow_free_text: true }} onAnswer={onAnswer} />);
  fireEvent.click(screen.getByText("≤ 750 €"));
  expect(onAnswer).toHaveBeenCalledWith(750);
});

test("renders long options as a full-width, text-wrapping vertical list", () => {
  const onAnswer = vi.fn();
  const longLabel = "Tenerife (TFS) — clima mite tutto l'anno, spiagge nere vulcaniche e ottimi voli diretti da Milano in agosto";
  render(<QuestionChips q={{ type: "question", id: "selected_destination", text: "Quale destinazione?",
    options: [{ label: longLabel, value: "TFS" }], allow_free_text: true }} onAnswer={onAnswer} />);
  const btn = screen.getByText(longLabel);
  expect(btn.className).toMatch(/whitespace-normal/);
  expect(btn.className).toMatch(/w-full/);
  expect(btn.className).toMatch(/text-left/);
  fireEvent.click(btn);
  expect(onAnswer).toHaveBeenCalledWith("TFS");
});

test("renders each option's description as muted sub-text under the label", () => {
  const onAnswer = vi.fn();
  render(<QuestionChips q={{ type: "question", id: "selected_destination", text: "Quale destinazione?",
    options: [
      { label: "Atene (ATH)", value: "ATH", description: "Acropoli, musei e cucina greca." },
      { label: "Creta (HER)", value: "HER", description: "Spiagge e sito di Cnosso." },
    ], allow_free_text: true }} onAnswer={onAnswer} />);
  expect(screen.getByText("Acropoli, musei e cucina greca.")).toBeInTheDocument();
  expect(screen.getByText("Spiagge e sito di Cnosso.")).toBeInTheDocument();
  // the option button is still clickable
  fireEvent.click(screen.getByText("Atene (ATH)"));
  expect(onAnswer).toHaveBeenCalledWith("ATH");
});

test("option button does not force horizontal overflow (inner span is constrained)", () => {
  const onAnswer = vi.fn();
  const longLabel = "Tenerife (TFS) — clima mite tutto l'anno e ottimi voli diretti";
  const longDesc = "Una descrizione lunghissima senza spazi-brevi che potrebbe altrimenti forzare uno scroll orizzontale del contenitore della chat";
  render(<QuestionChips q={{ type: "question", id: "selected_destination", text: "Quale destinazione?",
    options: [{ label: longLabel, value: "TFS", description: longDesc }], allow_free_text: true }} onAnswer={onAnswer} />);
  // The inner stacked span that holds label + description is width-constrained so
  // long text wraps instead of pushing the column wider.
  const desc = screen.getByText(longDesc);
  const inner = desc.parentElement!;
  expect(inner.className).toMatch(/min-w-0/);
  expect(inner.className).toMatch(/w-full/);
});

test("multi-select: a selected option's description contrasts with the dark bg (not muted)", () => {
  const onAnswer = vi.fn();
  render(<QuestionChips q={{ type: "question", id: "selected_destination", text: "Quali destinazioni?",
    multi_select: true,
    options: [
      { label: "Atene (ATH)", value: "ATH", description: "Acropoli, musei e cucina greca." },
    ], allow_free_text: false }} onAnswer={onAnswer} />);

  const desc = screen.getByText("Acropoli, musei e cucina greca.");
  const label = screen.getByText("Atene (ATH)");
  // Before selection: description is muted (readable on the light/secondary bg).
  expect(desc.className).toMatch(/text-muted-foreground/);

  // Select the option -> dark teal (primary) background.
  fireEvent.click(screen.getByRole("button", { name: /Atene \(ATH\)/ }));

  // Now the description must NOT be dark muted text on the dark bg; it must use a
  // contrasting primary-foreground tint. The label likewise stays on a contrasting color.
  expect(desc.className).not.toMatch(/text-muted-foreground/);
  expect(desc.className).toMatch(/text-primary-foreground/);
  expect(label.className).toMatch(/text-primary-foreground/);
});

test("multi-select: toggling options and confirming submits a comma-joined answer", () => {
  const onAnswer = vi.fn();
  render(<QuestionChips q={{ type: "question", id: "selected_destination", text: "Quali destinazioni?",
    multi_select: true,
    options: [
      { label: "Creta (HER)", value: "HER" },
      { label: "Tenerife (TFS)", value: "TFS" },
      { label: "Atene (ATH)", value: "ATH" },
    ], allow_free_text: true }} onAnswer={onAnswer} />);

  const confirm = screen.getByRole("button", { name: /conferma/i });
  // Disabled until at least one option is selected.
  expect(confirm).toBeDisabled();

  const her = screen.getByRole("button", { name: /Creta \(HER\)/ });
  const tfs = screen.getByRole("button", { name: /Tenerife \(TFS\)/ });
  fireEvent.click(her);
  fireEvent.click(tfs);
  expect(her).toHaveAttribute("aria-pressed", "true");
  expect(tfs).toHaveAttribute("aria-pressed", "true");
  // Clicking an option does NOT immediately answer in multi-select mode.
  expect(onAnswer).not.toHaveBeenCalled();

  expect(confirm).not.toBeDisabled();
  fireEvent.click(confirm);
  expect(onAnswer).toHaveBeenCalledTimes(1);
  expect(onAnswer).toHaveBeenCalledWith("HER,TFS");
});

test("multi-select: clicking a selected option again deselects it", () => {
  const onAnswer = vi.fn();
  render(<QuestionChips q={{ type: "question", id: "selected_destination", text: "Quali destinazioni?",
    multi_select: true,
    options: [
      { label: "Creta (HER)", value: "HER" },
      { label: "Tenerife (TFS)", value: "TFS" },
    ], allow_free_text: false }} onAnswer={onAnswer} />);
  const her = screen.getByRole("button", { name: /Creta \(HER\)/ });
  fireEvent.click(her);
  expect(her).toHaveAttribute("aria-pressed", "true");
  fireEvent.click(her);
  expect(her).toHaveAttribute("aria-pressed", "false");
  expect(screen.getByRole("button", { name: /conferma/i })).toBeDisabled();
});
