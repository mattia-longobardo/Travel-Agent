"use client";
import { ClipboardList, Luggage, MessageSquare } from "lucide-react";

export type MobileTab = "chat" | "brief" | "risultati";

const TABS: { key: MobileTab; label: string; icon: typeof MessageSquare }[] = [
  { key: "chat", label: "Pianifica", icon: MessageSquare },
  { key: "risultati", label: "Risultati", icon: Luggage },
  { key: "brief", label: "Riepilogo", icon: ClipboardList },
];

export function MobileTabBar({ active, onTab, resultCount = 0 }: {
  active: MobileTab;
  onTab: (t: MobileTab) => void;
  resultCount?: number;
}) {
  const cell = "relative flex min-h-16 flex-1 flex-col items-center justify-center gap-1 px-2 py-2 text-xs font-semibold";
  return (
    <nav
      role="tablist"
      aria-label="Navigazione"
      className="flex shrink-0 items-stretch border-t bg-background/95 pb-[env(safe-area-inset-bottom)] shadow-[0_-4px_16px_rgba(0,0,0,0.06)] backdrop-blur"
    >
      {TABS.map(({ key, label, icon: Icon }) => {
        const isActive = active === key;
        return (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onTab(key)}
            className={cell + (isActive ? " text-primary" : " text-muted-foreground")}
          >
            <span className={"relative grid size-7 place-items-center rounded-full " + (isActive ? "bg-primary/10" : "")}>
              <Icon aria-hidden="true" className="size-5" />
              {key === "risultati" && resultCount > 0 && (
                <span className="absolute -right-2 -top-1 grid min-w-5 place-items-center rounded-full bg-[var(--travel-coral)] px-1 text-[10px] leading-5 text-white">
                  {resultCount > 99 ? "99+" : resultCount}
                </span>
              )}
            </span>
            {label}
          </button>
        );
      })}
    </nav>
  );
}
