"use client";
import { Button } from "@/components/ui/button";

const OPTS: { value: string; label: string }[] = [
  { value: "7d", label: "7g" }, { value: "30d", label: "30g" },
  { value: "90d", label: "90g" }, { value: "all", label: "Tutto" },
];

export function TimeRangeSelector({ value, onChange }: { value: string; onChange: (r: string) => void }) {
  return (
    <div className="flex gap-1 rounded-lg bg-muted p-1">
      {OPTS.map((o) => (
        <Button key={o.value} type="button" size="sm"
          variant={value === o.value ? "default" : "ghost"}
          onClick={() => onChange(o.value)}>{o.label}</Button>
      ))}
    </div>
  );
}
