import { parseSSEChunk } from "@/lib/sse";

test("parses multiple data lines", () => {
  const buf = 'data: {"type":"agent_step","agent":"intake","status":"running","label":"x"}\n\n' +
              'data: {"type":"done"}\n\n';
  const { events, rest } = parseSSEChunk(buf);
  expect(events.length).toBe(2);
  expect(events[0].type).toBe("agent_step");
  expect(rest).toBe("");
});

test("keeps incomplete trailing line in rest", () => {
  const { events, rest } = parseSSEChunk('data: {"type":"done"}\n\ndata: {"type":"mes');
  expect(events.length).toBe(1);
  expect(rest.startsWith("data:")).toBe(true);
});

import { streamChat } from "@/lib/sse";

test("passes the abort signal to fetch and swallows AbortError", async () => {
  const ctrl = new AbortController();
  const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
    expect(init.signal).toBe(ctrl.signal);
    return {
      body: {
        getReader: () => ({
          read: async () => { throw new DOMException("aborted", "AbortError"); },
        }),
      },
    } as unknown as Response;
  });
  vi.stubGlobal("fetch", fetchMock);
  await expect(
    streamChat("/api/chats/1/messages", {}, () => {}, ctrl.signal),
  ).resolves.toBeUndefined();   // AbortError must NOT reject
  expect(fetchMock).toHaveBeenCalled();
  vi.unstubAllGlobals();
});
