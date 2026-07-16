import { render, screen, fireEvent } from "@testing-library/react";
import { MobileConsole } from "@/components/mobile/MobileConsole";
import type { PackageCardData } from "@/lib/types";

// Minimal valid PackageCardData fixture (mirrors packagecard.test.tsx style)
function makePkg(id: string, price: number): PackageCardData {
  return {
    id,
    kind: "package",
    badge: null,
    destination: `Destinazione ${id}`,
    price_per_person: price,
    price_total: price * 2,
    currency: "EUR",
    nights: 7,
    booking_url: `https://example.com/${id}`,
  };
}

const base = {
  user: null, chats: [], groups: [], view: "active" as const, activeChatId: null,
  actions: { onSelect: () => {}, onArchive: () => {}, onTrash: () => {}, onRestore: () => {}, onDeleteForever: () => {}, onShare: () => {}, onMove: () => {}, onRename: () => {} },
  onNew: () => {}, onView: () => {}, onEmptyTrash: () => {},
  title: "Nuovo viaggio", hasActive: false,
  onShare: () => {}, onExport: () => {}, onRename: () => {}, onArchive: () => {}, onTrash: () => {},
  messages: [], sending: false, onStop: () => {}, steps: [], error: null, question: null,
  draft: "", setDraft: () => {}, handleSend: () => {}, onPickEmpty: () => {},
  searchMode: "flight_hotel" as const, accommodationType: "both" as const,
  onSearchModeChange: () => {}, onAccommodationTypeChange: () => {},
  brief: null,
  packages: [], resultBatches: [], selectedResultBatchId: null, onSelectResultBatch: () => {},
  chatItems: [], locationGroups: [], selectedLocation: null, onSelectLocation: () => {},
  onExportExcel: () => {},
};

test("parte sul tab Pianifica e mostra lo stato vuoto", () => {
  render(<MobileConsole {...base} />);
  expect(screen.getByRole("tab", { name: /pianifica/i })).toHaveAttribute("aria-selected", "true");
});

test("se arrivano risultati mostra badge e pulsante per raggiungerli", () => {
  const pkg = makePkg("nuovo", 520);
  render(<MobileConsole {...base} packages={[pkg]} chatItems={[pkg]} />);
  expect(screen.getByRole("button", { name: /vedi 1 risultato/i })).toBeInTheDocument();
  expect(screen.getByText("1", { selector: "span" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /vedi 1 risultato/i }));
  expect(screen.getByRole("tab", { name: /risultati/i })).toHaveAttribute("aria-selected", "true");
});

test("cambia al tab Riepilogo", () => {
  render(<MobileConsole {...base} />);
  fireEvent.click(screen.getByRole("tab", { name: /riepilogo/i }));
  expect(screen.getByRole("tab", { name: /riepilogo/i })).toHaveAttribute("aria-selected", "true");
});

test("tab Risultati mostra una card compatta per ogni chatItem (più di 4)", () => {
  // Create 6 packages — more than the old ResultsPanel slice(0,4) cap
  const pkgs = Array.from({ length: 6 }, (_, i) => makePkg(`p${i + 1}`, 500 + i * 50));
  render(
    <MobileConsole
      {...base}
      packages={pkgs}
      chatItems={pkgs}
      hasActive={true}
    />
  );
  // Navigate to the Risultati tab
  fireEvent.click(screen.getByRole("tab", { name: /risultati/i }));
  // All 6 offers should be visible (one MobilePackageCard link per item)
  const links = screen.getAllByRole("link", { name: /vai all'offerta/i });
  expect(links.length).toBeGreaterThan(4);
  expect(links.length).toBe(6);
  // The badge shows the correct count
  expect(screen.getByText("6 opzioni")).toBeInTheDocument();
});

test("tab Risultati permette di selezionare un batch precedente", () => {
  const first = makePkg("prima", 500);
  const latest = makePkg("ultima", 650);
  const onSelectResultBatch = vi.fn();
  render(
    <MobileConsole
      {...base}
      packages={[latest]}
      resultBatches={[
        { id: "message-1", packages: [first] },
        { id: "message-2", packages: [latest] },
      ]}
      selectedResultBatchId="message-2"
      onSelectResultBatch={onSelectResultBatch}
      chatItems={[latest]}
    />
  );
  fireEvent.click(screen.getByRole("tab", { name: /risultati/i }));
  fireEvent.change(screen.getByRole("combobox", { name: /ricerca precedente/i }), {
    target: { value: "message-1" },
  });
  expect(onSelectResultBatch).toHaveBeenCalledWith("message-1");
});

test("menu azioni si chiude al click esterno", () => {
  render(<MobileConsole {...base} hasActive={true} />);
  // Open the menu
  const menuBtn = screen.getByRole("button", { name: /azioni/i });
  fireEvent.click(menuBtn);
  // Menu should be open (Condividi item visible)
  expect(screen.getByText("Condividi")).toBeInTheDocument();
  // Fire a mousedown outside the menu container
  fireEvent.mouseDown(document.body);
  // Menu should be closed
  expect(screen.queryByText("Condividi")).not.toBeInTheDocument();
});

test("menu azioni si chiude premendo Escape", () => {
  render(<MobileConsole {...base} hasActive={true} />);
  const menuBtn = screen.getByRole("button", { name: /azioni/i });
  fireEvent.click(menuBtn);
  expect(screen.getByText("Condividi")).toBeInTheDocument();
  fireEvent.keyDown(document, { key: "Escape" });
  expect(screen.queryByText("Condividi")).not.toBeInTheDocument();
});

test("mobile: 'Genera altre opzioni' arriva a handleSend con generateMore (regressione)", () => {
  // Bug: MobileConsole scartava le opts di QuestionChips, quindi il toggle era ignorato su mobile.
  const calls: Array<[string, string | undefined, { generateMore?: boolean; refineText?: string } | undefined]> = [];
  const question = {
    type: "question" as const,
    id: "selected_destination",
    text: "Scegli una destinazione",
    multi_select: true,
    allow_free_text: true,
    options: [{ label: "Atene", value: "ATH" }],
  };
  render(
    <MobileConsole
      {...base}
      hasActive={true}
      question={question}
      handleSend={(t, a, o) => calls.push([t, a, o])}
    />
  );
  fireEvent.click(screen.getByRole("checkbox", { name: /genera altre opzioni/i }));
  fireEvent.click(screen.getByRole("button", { name: /conferma risposta/i }));
  expect(calls).toHaveLength(1);
  expect(calls[0][1]).toBe("selected_destination");
  expect(calls[0][2]).toEqual({ generateMore: true });
});
