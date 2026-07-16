import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import Page from "@/app/page";
import * as uc from "@/lib/useChat";
import * as api from "@/lib/api";
import * as geo from "@/lib/geo";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("@/lib/api", () => {
  const chatFixture = { id: 1, title: "Chat", params_json: {}, owner_id: 1, permission: "owner", status: "active", chat_group_id: null };
  return ({
  me: vi.fn().mockResolvedValue({ id: 1, username: "Test", email: "t@e.it", is_admin: true }),
  listChats: vi.fn().mockResolvedValue([chatFixture]),
  getChat: vi.fn().mockResolvedValue(chatFixture),
  getMessages: vi.fn().mockResolvedValue([]),
  createChat: vi.fn(),
  patchChat: vi.fn(),
  deleteChat: vi.fn(),
  listChatGroups: vi.fn().mockResolvedValue([]),
  createChatGroup: vi.fn(),
  renameChatGroup: vi.fn(),
  deleteChatGroup: vi.fn(),
  setChatStatus: vi.fn(),
  moveChatToGroup: vi.fn(),
  emptyTrash: vi.fn(),
  });
});

const base = {
  steps: [], packages: [], resultBatches: [], selectedResultBatchId: null,
  selectResultBatch: vi.fn(), question: null, messages: [], brief: null, error: null,
  sending: false, send: vi.fn(), hydrate: vi.fn(), reset: vi.fn(),
  setSending: vi.fn(),
};

// Each test stubs useChat with vi.spyOn; restore between tests so a leaked spy
// doesn't break the test that exercises the real hook (pending_question resume).
afterEach(() => { vi.clearAllMocks(); vi.restoreAllMocks(); });

test("empty state shows example prompts", () => {
  vi.spyOn(uc, "useChat").mockReturnValue(base as unknown as ReturnType<typeof uc.useChat>);
  render(<Page />);
  fireEvent.click(screen.getByText("Azzorre o Canarie ad agosto"));
  expect((screen.getByPlaceholderText(/descrivi date/i) as HTMLInputElement).value).toMatch(/Azzorre|Canarie/i);
});

test("desktop insight rail does not expose the Agents tab", () => {
  vi.spyOn(uc, "useChat").mockReturnValue(base as unknown as ReturnType<typeof uc.useChat>);
  render(<Page />);
  expect(screen.queryByRole("button", { name: "Agenti" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Brief viaggio" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Risultati" })).toBeInTheDocument();
});

test("sends the explicit screen mode and accommodation selector", async () => {
  const send = vi.fn().mockResolvedValue(undefined);
  vi.spyOn(uc, "useChat").mockReturnValue({ ...base, send } as unknown as ReturnType<typeof uc.useChat>);
  render(<Page />);
  await waitFor(() => expect(screen.getByRole("heading", { name: "Chat" })).toBeInTheDocument());
  fireEvent.click(screen.getByRole("tab", { name: /solo hotel/i }));
  fireEvent.click(screen.getByRole("radio", { name: /^case/i }));
  fireEvent.click(screen.getByRole("button", { name: /soggiorno al mare/i }));
  fireEvent.click(screen.getByRole("button", { name: /cerca/i }));
  await waitFor(() => expect(send).toHaveBeenCalled());
  expect(send.mock.calls[0][3]).toEqual(expect.objectContaining({
    searchMode: "hotel_only",
    accommodationType: "home",
  }));
});

test("renders package carousel when packages present", () => {
  vi.spyOn(uc, "useChat").mockReturnValue({
    ...base,
    packages: [{ id: "pkg-1", kind: "package", badge: null, destination: "Tenerife (TFS)",
      price_per_person: 690, price_total: 1380, currency: "EUR", nights: 7 }],
  } as unknown as ReturnType<typeof uc.useChat>);
  render(<Page />);
  expect(screen.getByText("Tenerife (TFS)")).toBeInTheDocument();
});

test("rehydrates every persisted assistant result batch, not only the latest", async () => {
  const hydrate = vi.fn();
  vi.spyOn(uc, "useChat").mockReturnValue({ ...base, hydrate } as unknown as ReturnType<typeof uc.useChat>);
  vi.mocked(api.getMessages).mockResolvedValue([
    { id: 1, role: "assistant", content: "Prima ricerca", created_at: "2026-07-01T10:00:00Z",
      tool_calls_json: { ranked: [{ id: "old", kind: "package", badge: null, destination: "Roma",
        price_per_person: 500, price_total: 1000, currency: "EUR", nights: 3 }] } },
    { id: 2, role: "assistant", content: "Seconda ricerca", created_at: "2026-07-01T11:00:00Z",
      tool_calls_json: { ranked: [{ id: "new", kind: "hotel_only", badge: null, destination: "Firenze",
        price_per_person: 300, price_total: 600, currency: "EUR", nights: 2 }] } },
  ] as never);

  render(<Page />);

  await waitFor(() => expect(hydrate).toHaveBeenCalled());
  const input = hydrate.mock.calls.at(-1)?.[0];
  expect(input.resultBatches).toEqual([
    expect.objectContaining({ id: "message-1", packages: [expect.objectContaining({ id: "old" })] }),
    expect.objectContaining({ id: "message-2", packages: [expect.objectContaining({ id: "new" })] }),
  ]);
});

test("single location shows no location selector", () => {
  vi.spyOn(uc, "useChat").mockReturnValue({
    ...base,
    packages: [
      { id: "a", kind: "package", badge: null, destination: "Tenerife (TFS)", dest_iata: "TFS", dest_name: "Tenerife", price_per_person: 690, price_total: 1380, currency: "EUR", nights: 7 },
      { id: "b", kind: "package", badge: null, destination: "Tenerife (TFS)", dest_iata: "TFS", dest_name: "Tenerife", price_per_person: 720, price_total: 1440, currency: "EUR", nights: 7 },
    ],
  } as unknown as ReturnType<typeof uc.useChat>);
  render(<Page />);
  expect(screen.queryAllByRole("tablist", { name: "Località" })).toHaveLength(0);
});

test("multiple locations render a shared selector; clicking the second shows its cards", () => {
  vi.spyOn(uc, "useChat").mockReturnValue({
    ...base,
    packages: [
      { id: "a", kind: "package", badge: null, destination: "Tenerife (TFS)", dest_iata: "TFS", dest_name: "Tenerife", price_per_person: 690, price_total: 1380, currency: "EUR", nights: 7, hotel_name: "Hotel Sol" },
      { id: "b", kind: "package", badge: null, destination: "Creta (HER)", dest_iata: "HER", dest_name: "Creta", price_per_person: 540, price_total: 1080, currency: "EUR", nights: 7, hotel_name: "Hotel Knossos" },
    ],
  } as unknown as ReturnType<typeof uc.useChat>);
  render(<Page />);
  // A selector appears (in chat area and sidebar both render a tablist).
  const tablists = screen.getAllByRole("tablist", { name: "Località" });
  expect(tablists.length).toBeGreaterThanOrEqual(1);
  // First location's card is visible by default.
  expect(screen.getAllByText("Tenerife (TFS)").length).toBeGreaterThan(0);
  expect(screen.queryByText("Creta (HER)")).not.toBeInTheDocument();
  // Click the "Creta" tab (use the first selector's tab).
  const cretaTab = within(tablists[0]).getByRole("tab", { name: /Creta/ });
  fireEvent.click(cretaTab);
  expect(screen.getAllByText("Creta (HER)").length).toBeGreaterThan(0);
  expect(screen.queryByText("Tenerife (TFS)")).not.toBeInTheDocument();
});

test("renders markdown in assistant messages", () => {
  vi.spyOn(uc, "useChat").mockReturnValue({
    ...base,
    messages: [{ role: "assistant", content: "Ecco **Palma de Mallorca**" }],
  } as unknown as ReturnType<typeof uc.useChat>);
  render(<Page />);
  const strong = screen.getByText("Palma de Mallorca");
  expect(strong.tagName).toBe("STRONG");
});

test("shows date and time under a message", () => {
  vi.spyOn(uc, "useChat").mockReturnValue({
    ...base,
    messages: [{ role: "user", content: "Ciao", created_at: "2026-06-19T21:30:00.000Z" }],
  } as unknown as ReturnType<typeof uc.useChat>);
  render(<Page />);
  // Renders an it-IT short date + HH:mm time, regardless of runner timezone.
  expect(screen.getByText(/\d{1,2}\/\d{2}\/\d{2,4},?\s+\d{1,2}:\d{2}/)).toBeInTheDocument();
});

test("shows an animated loading indicator while sending", () => {
  vi.spyOn(uc, "useChat").mockReturnValue({
    ...base,
    sending: true,
  } as unknown as ReturnType<typeof uc.useChat>);
  render(<Page />);
  expect(screen.getByRole("status", { name: /elaborando/i })).toBeInTheDocument();
});

test("moving the active chat to trash closes it", async () => {
  vi.spyOn(uc, "useChat").mockReturnValue(base as unknown as ReturnType<typeof uc.useChat>);
  vi.mocked(api.setChatStatus).mockResolvedValue({} as never);
  render(<Page />);
  // The active chat title is shown in the header.
  await waitFor(() => expect(screen.getByRole("heading", { name: "Chat" })).toBeInTheDocument());
  // Open the header menu and move the active chat to trash.
  fireEvent.click(screen.getByRole("button", { name: "Menu" }));
  fireEvent.click(screen.getByText("Sposta nel cestino"));
  await waitFor(() => expect(api.setChatStatus).toHaveBeenCalledWith(1, "trashed"));
  // It is now closed: the header falls back to the "Nuovo viaggio" placeholder.
  await waitFor(() => expect(screen.getByRole("heading", { name: "Nuovo viaggio" })).toBeInTheDocument());
});

test("with no chats it does not eagerly create one (lazy new chat)", async () => {
  vi.spyOn(uc, "useChat").mockReturnValue(base as unknown as ReturnType<typeof uc.useChat>);
  vi.mocked(api.listChats).mockResolvedValue([]);
  render(<Page />);
  await waitFor(() => expect(screen.getByRole("heading", { name: "Nuovo viaggio" })).toBeInTheDocument());
  expect(api.createChat).not.toHaveBeenCalled();
});

test("sending the first message lazily creates the chat then sends to it", async () => {
  const sendMock = vi.fn().mockResolvedValue(undefined);
  vi.spyOn(uc, "useChat").mockReturnValue({ ...base, send: sendMock } as unknown as ReturnType<typeof uc.useChat>);
  vi.mocked(api.listChats).mockResolvedValue([]);
  vi.mocked(api.createChat).mockResolvedValue({
    id: 99, title: "Nuova chat", params_json: {}, owner_id: 1, permission: "owner", status: "active", chat_group_id: null,
  } as never);
  vi.mocked(api.patchChat).mockResolvedValue({ id: 99, title: "Ciao" } as never);
  render(<Page />);
  await waitFor(() => expect(screen.getByRole("heading", { name: "Nuovo viaggio" })).toBeInTheDocument());
  const input = screen.getByPlaceholderText(/descrivi date/i);
  fireEvent.change(input, { target: { value: "Ciao" } });
  fireEvent.click(screen.getByRole("button", { name: "Cerca" }));
  await waitFor(() => expect(api.createChat).toHaveBeenCalledTimes(1));
  expect(sendMock).toHaveBeenCalledWith("Ciao", undefined, 99, expect.objectContaining({
    onChatTitle: expect.any(Function),
  }));
  expect(api.patchChat).not.toHaveBeenCalled();
});

test("re-shows the question chips when a chat has a persisted pending_question", async () => {
  // Use the real useChat so the hydrate effect drives the question back into view.
  vi.spyOn(geo, "getCoords").mockResolvedValue([45.46, 9.19]);
  const pending = {
    type: "question", id: "selected_destination", text: "Quale destinazione preferisci?",
    options: [{ label: "Tenerife (TFS)", value: "TFS" }], allow_free_text: true,
  };
  const chatFixture = {
    id: 1, title: "Chat", params_json: { pending_question: pending },
    owner_id: 1, permission: "owner", status: "active", chat_group_id: null,
  };
  vi.mocked(api.listChats).mockResolvedValue([chatFixture as never]);
  vi.mocked(api.getChat).mockResolvedValue(chatFixture as never);
  vi.mocked(api.getMessages).mockResolvedValue([
    { id: 1, role: "user", content: "Canarie o Azzorre?", tool_calls_json: null, created_at: "2026-06-19T21:30:00.000Z" },
  ] as never);

  render(<Page />);

  await waitFor(() =>
    expect(screen.getByText("Quale destinazione preferisci?")).toBeInTheDocument(),
  );
  expect(screen.getByText("Tenerife (TFS)")).toBeInTheDocument();
});

test("resumes a still-running search after reload (shows the working state)", async () => {
  // Reloading mid-search: the backend run is detached and still in progress (run_active),
  // so the page must show the working state and poll, instead of looking idle/interrupted.
  vi.spyOn(geo, "getCoords").mockResolvedValue([45.46, 9.19]);
  const chatFixture = {
    id: 1, title: "Chat", params_json: { run_active: true },
    owner_id: 1, permission: "owner", status: "active", chat_group_id: null,
  };
  vi.mocked(api.listChats).mockResolvedValue([chatFixture as never]);
  vi.mocked(api.getChat).mockResolvedValue(chatFixture as never);
  vi.mocked(api.getMessages).mockResolvedValue([
    { id: 1, role: "user", content: "Canarie agosto", tool_calls_json: null, created_at: "2026-06-19T21:30:00.000Z" },
  ] as never);

  render(<Page />);

  await waitFor(() =>
    expect(screen.getByRole("status", { name: /elaborando/i })).toBeInTheDocument(),
  );
});

// A trashed chat is only ever returned by listChats("trashed"); every other view
// (and the initial mount) sees a single active chat.
function trashViewApi(trashed = { id: 7, title: "Vecchia", params_json: {}, owner_id: 1, permission: "owner", status: "trashed", chat_group_id: null }) {
  const active = { id: 1, title: "Chat", params_json: {}, owner_id: 1, permission: "owner", status: "active", chat_group_id: null };
  vi.mocked(api.listChats).mockImplementation(
    async (status?: string) => (status === "trashed" ? [trashed] : [active]) as never,
  );
}
// Reload targets seen since the mock was last cleared. Any "active" reload means the
// view was switched away from the trash (the bug); a trash-only refresh means we stayed.
function reloadTargets() {
  return vi.mocked(api.listChats).mock.calls.map((c) => c[0]);
}

test("deleting a chat forever keeps you in the Cestino view", async () => {
  vi.spyOn(uc, "useChat").mockReturnValue(base as unknown as ReturnType<typeof uc.useChat>);
  trashViewApi();
  vi.mocked(api.deleteChat).mockResolvedValue(undefined as never);
  render(<Page />);
  // Switch to the trash, where the trashed chat row is shown.
  fireEvent.click(await screen.findByText("Cestino"));
  await waitFor(() => expect(screen.getByText("Vecchia")).toBeInTheDocument());
  // Forget the reloads done up to here; only the post-delete refresh matters.
  vi.mocked(api.listChats).mockClear();
  // Open its row menu and delete it forever.
  fireEvent.click(screen.getByRole("button", { name: "Azioni chat" }));
  fireEvent.click(screen.getByText("Elimina definitivamente"));
  await waitFor(() => expect(api.deleteChat).toHaveBeenCalledWith(7));
  // The refresh after deletion stays on the trash — we are NOT bounced to the active view.
  await waitFor(() => expect(reloadTargets().length).toBeGreaterThan(0));
  expect(reloadTargets()).not.toContain("active");
  expect(reloadTargets()).toContain("trashed");
});

test("emptying the trash keeps you in the Cestino view", async () => {
  vi.spyOn(uc, "useChat").mockReturnValue(base as unknown as ReturnType<typeof uc.useChat>);
  trashViewApi();
  vi.mocked(api.emptyTrash).mockResolvedValue(undefined as never);
  render(<Page />);
  fireEvent.click(await screen.findByText("Cestino"));
  await waitFor(() => expect(screen.getByText("Vecchia")).toBeInTheDocument());
  vi.mocked(api.listChats).mockClear();
  fireEvent.click(screen.getByRole("button", { name: /Svuota cestino/i }));
  await waitFor(() => expect(api.emptyTrash).toHaveBeenCalled());
  await waitFor(() => expect(reloadTargets().length).toBeGreaterThan(0));
  expect(reloadTargets()).not.toContain("active");
  expect(reloadTargets()).toContain("trashed");
});
