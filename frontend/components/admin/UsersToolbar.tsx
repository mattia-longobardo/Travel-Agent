"use client";
import { useEffect, useRef, useState } from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import type { UsersFilters } from "@/lib/api";

type GroupOpt = { id: number; name: string };
const selectCls = "h-9 rounded-lg border border-input bg-background px-2 text-sm";

export function UsersToolbar({ filters, groups, pageSize, onFilters, onPageSize }: {
  filters: UsersFilters; groups: GroupOpt[]; pageSize: number;
  onFilters: (f: UsersFilters) => void; onPageSize: (n: number) => void;
}) {
  const [q, setQ] = useState(filters.q ?? "");
  const t = useRef<ReturnType<typeof setTimeout> | null>(null);
  const filtersRef = useRef(filters);
  useEffect(() => {
    filtersRef.current = filters;
  }, [filters]);
  useEffect(() => {
    if (t.current) clearTimeout(t.current);
    t.current = setTimeout(() => onFilters({ ...filtersRef.current, q: q || undefined }), 300);
    return () => { if (t.current) clearTimeout(t.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="relative min-w-56 flex-1">
        <Search aria-hidden className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input className="pl-8" placeholder="Cerca nome o email…" value={q}
          onChange={(e) => setQ(e.target.value)} />
      </div>
      <select aria-label="Stato" className={selectCls} value={filters.status ?? "all"}
        onChange={(e) => onFilters({ ...filters, status: e.target.value === "all" ? undefined : e.target.value })}>
        <option value="all">Tutti gli stati</option>
        <option value="active">Attivi</option>
        <option value="inactive">Disattivati</option>
      </select>
      <select aria-label="Ruolo" className={selectCls} value={filters.role ?? "all"}
        onChange={(e) => onFilters({ ...filters, role: e.target.value === "all" ? undefined : e.target.value })}>
        <option value="all">Tutti i ruoli</option>
        <option value="admin">Admin</option>
        <option value="user">Utenti</option>
      </select>
      <select aria-label="Gruppo" className={selectCls} value={filters.group_id ?? ""}
        onChange={(e) => onFilters({ ...filters, group_id: e.target.value ? Number(e.target.value) : undefined })}>
        <option value="">Tutti i gruppi</option>
        {groups.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
      </select>
      <select aria-label="Per pagina" className={selectCls} value={pageSize}
        onChange={(e) => onPageSize(Number(e.target.value))}>
        {[25, 50, 100, 200].map((n) => <option key={n} value={n}>{n}/pagina</option>)}
      </select>
    </div>
  );
}
