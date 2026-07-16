"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { BarChart3, ChevronDown, LogOut, Settings, Users } from "lucide-react";
import { logout } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import type { Me } from "@/lib/types";

function initials(name?: string) {
  if (!name) return "·";
  return name.trim().slice(0, 2).toUpperCase();
}

export function AccountMenu({ user }: { user: Me | null }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  async function doLogout() {
    await logout();
    router.push("/login");
  }

  return (
    <div ref={ref} className="relative flex items-center gap-3 border-t pt-4">
      <span className="grid size-9 place-items-center rounded-lg bg-[var(--travel-coral-soft)] text-sm font-semibold text-[var(--travel-coral)]">
        {initials(user?.username)}
      </span>
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium">{user?.username ?? "—"}</div>
        <div className="truncate text-xs text-muted-foreground">{user?.email ?? ""}</div>
      </div>
      <Button type="button" variant="ghost" size="icon-sm" aria-label="Account"
        aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        <ChevronDown aria-hidden="true" />
      </Button>
      {open && (
        <div role="menu" className="absolute bottom-14 right-0 z-10 w-48 rounded-lg border bg-popover p-1 shadow-lg">
          <div className="px-2 py-1.5 text-xs text-muted-foreground">{user?.email ?? ""}</div>
          <button type="button" role="menuitem" onClick={() => router.push("/settings")}
            className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm hover:bg-accent">
            <Settings aria-hidden="true" className="size-4" />
            Impostazioni
          </button>
          {user?.is_admin && (
            <button type="button" role="menuitem" onClick={() => router.push("/admin/users")}
              className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm hover:bg-accent">
              <Users aria-hidden="true" className="size-4" />
              Gestione utenti
            </button>
          )}
          {user?.is_admin && (
            <button type="button" role="menuitem" onClick={() => router.push("/admin/analytics")}
              className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm hover:bg-accent">
              <BarChart3 aria-hidden="true" className="size-4" />
              Analytics
            </button>
          )}
          <button type="button" role="menuitem" onClick={doLogout}
            className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm hover:bg-accent">
            <LogOut aria-hidden="true" className="size-4" />
            Esci
          </button>
        </div>
      )}
    </div>
  );
}
