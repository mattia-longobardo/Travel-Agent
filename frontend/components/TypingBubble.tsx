"use client";
import { Compass } from "lucide-react";

// Animated "agent is thinking" placeholder shown while the stream is in flight.
export function TypingBubble() {
  return (
    <div className="flex justify-start gap-3" aria-label="L'agente sta elaborando" role="status">
      <span className="mt-1 hidden size-9 shrink-0 place-items-center rounded-lg bg-primary text-primary-foreground shadow-sm sm:grid">
        <Compass aria-hidden="true" />
      </span>
      <div className="flex items-center gap-1.5 rounded-lg bg-card px-4 py-3 shadow-sm ring-1 ring-border">
        <span className="size-2 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:-0.3s]" />
        <span className="size-2 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:-0.15s]" />
        <span className="size-2 animate-bounce rounded-full bg-muted-foreground/60" />
        <span className="sr-only">L&apos;agente sta elaborando…</span>
      </div>
    </div>
  );
}
