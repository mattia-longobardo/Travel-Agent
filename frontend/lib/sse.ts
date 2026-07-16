import type { ChatEvent } from "./types";

export function parseSSEChunk(buf: string): { events: ChatEvent[]; rest: string } {
  const parts = buf.split("\n\n");
  const rest = parts.pop() ?? "";
  const events: ChatEvent[] = [];
  for (const block of parts) {
    const line = block.split("\n").find((l) => l.startsWith("data:"));
    if (!line) continue;
    try {
      events.push(JSON.parse(line.slice(5).trim()));
    } catch {
      /* skip */
    }
  }
  return { events, rest };
}

export async function streamChat(
  url: string,
  payload: unknown,
  onEvent: (e: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  let resp: Response;
  try {
    resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(payload),
      signal,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") return;
    throw e;
  }
  if (!resp.body) throw new Error("no stream");
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const { events, rest } = parseSSEChunk(buf);
      buf = rest;
      events.forEach(onEvent);
    }
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") return;  // user pressed Stop
    throw e;
  }
}
