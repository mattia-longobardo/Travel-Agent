"use client";
import { SendHorizontal, Square } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export function ChatComposer({ value, onChange, onSend, disabled, sending, onStop, placeholder = "Descrivi date, budget e stile del viaggio..." }: {
  value: string; onChange: (v: string) => void; onSend: () => void; disabled: boolean;
  sending: boolean; onStop: () => void; placeholder?: string;
}) {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (value.trim()) onSend();
      }}
      className="flex gap-2"
    >
      <div className="flex min-h-14 flex-1 items-center gap-2 rounded-lg border bg-card px-3 shadow-lg ring-1 ring-primary/10 focus-within:border-primary/60 focus-within:ring-primary/20">
        <Input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder={placeholder}
          className="h-11 border-0 px-0 text-base shadow-none focus-visible:ring-0 md:text-sm"
        />
        {sending ? (
          <Button
            type="button"
            onClick={onStop}
            size="icon-lg"
            variant="destructive"
            aria-label="Interrompi"
          >
            <Square aria-hidden="true" />
          </Button>
        ) : (
          <Button
            type="submit"
            disabled={disabled || !value.trim()}
            size="icon-lg"
            aria-label="Cerca"
          >
            <SendHorizontal aria-hidden="true" />
          </Button>
        )}
      </div>
    </form>
  );
}
