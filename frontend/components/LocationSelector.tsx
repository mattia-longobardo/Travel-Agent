"use client";
import type { LocationGroup } from "@/lib/grouping";

export function LocationSelector({
  groups,
  selected,
  onSelect,
  className,
}: {
  groups: LocationGroup[];
  selected: string;
  onSelect: (key: string) => void;
  className?: string;
}) {
  return (
    <div
      role="tablist"
      aria-label="Località"
      className={
        "flex flex-wrap gap-1 rounded-lg bg-muted p-1 text-sm font-medium " + (className ?? "")
      }
    >
      {groups.map((g) => {
        const active = g.key === selected;
        return (
          <button
            key={g.key}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onSelect(g.key)}
            className={
              "min-w-0 rounded-md px-2.5 py-1.5 transition " +
              (active
                ? "bg-background text-primary shadow-sm"
                : "text-muted-foreground hover:text-foreground")
            }
          >
            <span className="truncate">{g.label}</span>
            <span className="ml-1.5 text-xs text-muted-foreground">{g.items.length}</span>
          </button>
        );
      })}
    </div>
  );
}
