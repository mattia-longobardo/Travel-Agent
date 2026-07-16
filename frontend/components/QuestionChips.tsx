"use client";
import { useState } from "react";
import { Check, MessageCircleQuestion, SendHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { QuestionEvent, QuestionOption } from "@/lib/types";

function OptionLabel({ o, isSelected }: { o: QuestionOption; isSelected?: boolean }) {
  if (!o.description) return <>{o.label}</>;
  return (
    <span className="flex min-w-0 w-full flex-col gap-0.5">
      <span className={"break-words" + (isSelected ? " text-primary-foreground" : "")}>{o.label}</span>
      <span
        className={
          "break-words text-xs font-normal " +
          (isSelected ? "text-primary-foreground/80" : "text-muted-foreground")
        }
      >
        {o.description}
      </span>
    </span>
  );
}

export function QuestionChips({
  q,
  onAnswer,
}: {
  q: QuestionEvent;
  onAnswer: (v: string | number, opts?: { generateMore?: boolean; refineText?: string }) => void;
}) {
  const [free, setFree] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [more, setMore] = useState(false);
  const multi = !!q.multi_select;

  function toggle(value: string | number) {
    const key = String(value);
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  // Multi-select submit: combine selected chips + free text + the "more" toggle into one action.
  function submitMulti() {
    // Preserve option order in the joined answer.
    const ordered = q.options.map((o) => String(o.value)).filter((v) => selected.has(v));
    const hasChips = ordered.length > 0;
    const text = free.trim();
    if (hasChips) {
      const opts = more || text.length > 0
        ? { generateMore: true, refineText: text }
        : undefined;
      if (opts === undefined) onAnswer(ordered.join(","));
      else onAnswer(ordered.join(","), opts);
    } else if (text) {
      onAnswer(text, { generateMore: more });
    } else if (more) {
      onAnswer("", { generateMore: true });
    }
  }

  const canSubmitMulti = selected.size > 0 || free.trim().length > 0 || more;

  return (
    <section className="rounded-lg border bg-card p-4 shadow-sm">
      <div className="mb-3 flex items-start gap-3">
        <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
          <MessageCircleQuestion aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <p className="font-medium">{q.text}</p>
          <p className="text-sm text-muted-foreground">
            {multi
              ? "Scegli una o più opzioni, poi conferma."
              : "Scegli una opzione oppure rispondi liberamente."}
          </p>
        </div>
      </div>
      <div className="flex w-full min-w-0 flex-col gap-2">
        {q.options.map((o) => {
          const isSelected = multi && selected.has(String(o.value));
          return (
            <Button
              key={String(o.value)}
              variant={isSelected ? "default" : "secondary"}
              aria-pressed={multi ? isSelected : undefined}
              onClick={() => (multi ? toggle(o.value) : onAnswer(o.value))}
              className="h-auto w-full min-w-0 justify-start whitespace-normal py-2 text-left"
            >
              {multi && (
                <span
                  aria-hidden="true"
                  className={
                    "mt-0.5 grid size-4 shrink-0 place-items-center rounded border " +
                    (isSelected ? "border-current bg-current/0" : "border-current/40")
                  }
                >
                  {isSelected && <Check className="size-3" />}
                </span>
              )}
              <OptionLabel o={o} isSelected={isSelected} />
            </Button>
          );
        })}
      </div>
      {multi ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submitMulti();
          }}
          className="mt-3 flex flex-col gap-2"
        >
          <button
            type="button"
            role="checkbox"
            aria-checked={more}
            onClick={() => setMore((v) => !v)}
            className={
              "flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm transition-colors " +
              (more
                ? "border-primary bg-primary/10 text-foreground"
                : "border-input bg-background text-muted-foreground hover:bg-accent")
            }
          >
            <span
              aria-hidden="true"
              className={
                "grid size-4 shrink-0 place-items-center rounded border " +
                (more ? "border-primary bg-primary text-primary-foreground" : "border-current/40")
              }
            >
              {more && <Check className="size-3" />}
            </span>
            Genera altre opzioni
          </button>
          {q.allow_free_text && (
            <Input
              value={free}
              onChange={(e) => setFree(e.target.value)}
              placeholder="Oppure scrivi..."
            />
          )}
          <Button type="submit" className="w-full" disabled={!canSubmitMulti} aria-label="Conferma risposta">
            <SendHorizontal data-icon="inline-start" aria-hidden="true" />
            Conferma
          </Button>
        </form>
      ) : (
        q.allow_free_text && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (free.trim()) onAnswer(free.trim());
            }}
            className="mt-3 flex gap-2"
          >
            <Input
              value={free}
              onChange={(e) => setFree(e.target.value)}
              placeholder="Oppure scrivi..."
            />
            <Button type="submit" disabled={!free.trim()} aria-label="Invia risposta">
              <SendHorizontal data-icon="inline-start" aria-hidden="true" />
              Invia
            </Button>
          </form>
        )
      )}
    </section>
  );
}
