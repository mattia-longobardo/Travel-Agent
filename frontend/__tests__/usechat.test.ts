import { renderHook, act, waitFor } from "@testing-library/react";
import { useChat } from "@/lib/useChat";
import * as sse from "@/lib/sse";
import * as geo from "@/lib/geo";
import type { ChatEvent } from "@/lib/types";

test("accumulates packages and final message", async () => {
  vi.spyOn(geo, "getCoords").mockResolvedValue([45.46, 9.19]);
  vi.spyOn(sse, "streamChat").mockImplementation(async (_u, _p, onEvent) => {
    onEvent({ type: "agent_step", agent: "intake", status: "done", label: "x" });
    onEvent({ type: "package", data: { id: "pkg-1", kind: "package", badge: null,
      destination: "Tenerife (TFS)", price_per_person: 690, price_total: 1380, currency: "EUR", nights: 7 } });
    onEvent({ type: "message", content: "Ecco le proposte." });
    onEvent({ type: "done" });
  });
  const { result } = renderHook(() => useChat(1));
  await act(async () => { await result.current.send("Canarie agosto"); });
  await waitFor(() => expect(result.current.packages.length).toBe(1));
  expect(result.current.resultBatches).toHaveLength(1);
  expect(result.current.messages.at(-1)?.content).toBe("Ecco le proposte.");
  expect(result.current.sending).toBe(false);
});

test("captures brief event", async () => {
  vi.spyOn(geo, "getCoords").mockResolvedValue([45.46, 9.19]);
  vi.spyOn(sse, "streamChat").mockImplementation(async (_u, _p, onEvent) => {
    onEvent({ type: "brief", data: { destination_hint: "mare", date_from: "2026-08-16",
      date_to: null, window_from: null, window_to: null, trip_nights: null, dates_flexible: false,
      adults: 2, children_ages: [], budget_per_person: 800, currency: "EUR",
      min_stars: 4, origin_iata: ["MXP"] } });
    onEvent({ type: "done" });
  });
  const { result } = renderHook(() => useChat(1));
  await act(async () => { await result.current.send("mare agosto") });
  await waitFor(() => expect(result.current.brief?.budget_per_person).toBe(800));
});

test("captures generated chat title events", async () => {
  vi.spyOn(geo, "getCoords").mockResolvedValue([45.46, 9.19]);
  vi.spyOn(sse, "streamChat").mockImplementation(async (_u, _p, onEvent) => {
    onEvent({ type: "chat_title", chat_id: 1, title: "Canarie ad agosto" });
    onEvent({ type: "done" });
  });
  const { result } = renderHook(() => useChat(1));
  await act(async () => { await result.current.send("Canarie agosto") });
  await waitFor(() => expect(result.current.chatTitle?.title).toBe("Canarie ad agosto"));
});

test("sends the selected search and accommodation modes as structured fields", async () => {
  vi.spyOn(geo, "getCoords").mockResolvedValue([45.46, 9.19]);
  const stream = vi.spyOn(sse, "streamChat").mockImplementation(async (_u, _p, onEvent) => {
    onEvent({ type: "done" });
  });
  const { result } = renderHook(() => useChat(1));
  await act(async () => {
    await result.current.send("Roma a settembre", undefined, undefined, {
      searchMode: "hotel_only",
      accommodationType: "home",
    });
  });
  expect(stream).toHaveBeenCalledWith(
    expect.any(String),
    expect.objectContaining({ search_mode: "hotel_only", accommodation_type: "home" }),
    expect.any(Function),
    expect.any(AbortSignal),
  );
});

test("surfaces error event", async () => {
  vi.spyOn(geo, "getCoords").mockResolvedValue([45.46, 9.19]);
  vi.spyOn(sse, "streamChat").mockImplementation(async (_u, _p, onEvent) => {
    onEvent({ type: "error", message: "boom" });
    onEvent({ type: "done" });
  });
  const { result } = renderHook(() => useChat(1));
  await act(async () => { await result.current.send("x") });
  await waitFor(() => expect(result.current.error).toBe("boom"));
  expect(result.current.sending).toBe(false);
});

test("a later message without results keeps the previous result batch", async () => {
  vi.spyOn(geo, "getCoords").mockResolvedValue([45.46, 9.19]);
  let call = 0;
  vi.spyOn(sse, "streamChat").mockImplementation(async (_u, _p, onEvent) => {
    call += 1;
    if (call === 1) {
      onEvent({ type: "package", data: { id: "first", kind: "package", badge: null,
        destination: "Tenerife", price_per_person: 690, price_total: 1380, currency: "EUR", nights: 7 } });
    } else {
      onEvent({ type: "message", content: "Puoi raffinare ancora la richiesta." });
    }
    onEvent({ type: "done" });
  });
  const { result } = renderHook(() => useChat(1));

  await act(async () => { await result.current.send("Canarie agosto"); });
  await act(async () => { await result.current.send("Preferisco una zona tranquilla"); });

  expect(result.current.resultBatches).toHaveLength(1);
  expect(result.current.packages.map((item) => item.id)).toEqual(["first"]);
});

test("keeps multiple result batches and lets the user select an earlier one", async () => {
  vi.spyOn(geo, "getCoords").mockResolvedValue([45.46, 9.19]);
  let call = 0;
  vi.spyOn(sse, "streamChat").mockImplementation(async (_u, _p, onEvent) => {
    call += 1;
    onEvent({ type: "package", data: { id: `batch-${call}`, kind: "package", badge: null,
      destination: `Destinazione ${call}`, price_per_person: 500 + call, price_total: 1000, currency: "EUR", nights: 7 } });
    onEvent({ type: "done" });
  });
  const { result } = renderHook(() => useChat(1));

  await act(async () => { await result.current.send("Prima ricerca"); });
  const firstBatchId = result.current.selectedResultBatchId;
  await act(async () => { await result.current.send("Seconda ricerca"); });

  expect(result.current.resultBatches).toHaveLength(2);
  expect(result.current.packages[0].id).toBe("batch-2");
  act(() => { result.current.selectResultBatch(firstBatchId!); });
  expect(result.current.packages[0].id).toBe("batch-1");
});

test("hydrate restores messages and result batches, reset clears them", async () => {
  const { result } = renderHook(() => useChat(1));
  act(() => {
    result.current.hydrate({
      messages: [{ role: "user", content: "ciao" }, { role: "assistant", content: "ecco" }],
      resultBatches: [{ id: "message-2", packages: [{ id: "p1", kind: "package", badge: null, destination: "X",
        price_per_person: 100, price_total: 200, currency: "EUR", nights: 3 }] }],
      brief: null,
    });
  });
  expect(result.current.messages.length).toBe(2);
  expect(result.current.packages.length).toBe(1);
  expect(result.current.selectedResultBatchId).toBe("message-2");
  act(() => { result.current.reset(); });
  expect(result.current.messages.length).toBe(0);
  expect(result.current.packages.length).toBe(0);
  expect(result.current.resultBatches).toHaveLength(0);
});

test("hydrate restores a persisted pending question", () => {
  const { result } = renderHook(() => useChat(1));
  act(() => {
    result.current.hydrate({
      messages: [{ role: "user", content: "Canarie o Azzorre?" }],
      resultBatches: [],
      brief: null,
      question: { type: "question", id: "selected_destination", text: "Quale destinazione?",
        options: [{ label: "Tenerife", value: "TFS" }], allow_free_text: true },
    });
  });
  expect(result.current.question?.id).toBe("selected_destination");
});

test("cancel() posts to /stop and a stopped event ends the turn", async () => {
  vi.spyOn(geo, "getCoords").mockResolvedValue([45.46, 9.19]);
  let emit: ((e: ChatEvent) => void) | null = null;
  vi.spyOn(sse, "streamChat").mockImplementation(async (_u, _p, onEvent) => {
    emit = onEvent;
    onEvent({ type: "agent_step", agent: "intake", status: "running", label: "x" });
    // stay "open" until the test drives the stopped event
    await new Promise((r) => setTimeout(r, 50));
  });
  const fetchMock = vi.fn(async () => ({ json: async () => ({ stopped: true }) }) as unknown as Response);
  vi.stubGlobal("fetch", fetchMock);

  const { result } = renderHook(() => useChat(7));
  act(() => { void result.current.send("Canarie"); });
  await waitFor(() => expect(result.current.sending).toBe(true));

  await act(async () => { await result.current.cancel(); });
  expect(fetchMock).toHaveBeenCalledWith("/api/chats/7/stop", expect.objectContaining({ method: "POST" }));

  act(() => { emit!({ type: "stopped" }); });
  await waitFor(() => expect(result.current.sending).toBe(false));
  expect(result.current.messages.at(-1)?.content).toContain("interrotta");
  vi.unstubAllGlobals();
});
