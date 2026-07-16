"use client";
import { ArrowDown, ArrowUp, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { AdminUser } from "@/lib/api";

const COLS: { key: string; label: string }[] = [
  { key: "username", label: "Username" },
  { key: "email", label: "Email" },
  { key: "is_active", label: "Stato" },
];

export function UsersTable({ users, selected, sort, order, onToggle, onTogglePage, onSort, onRowClick }: {
  users: AdminUser[]; selected: Set<number>; sort: string; order: string;
  onToggle: (id: number, shift: boolean) => void; onTogglePage: () => void;
  onSort: (col: string) => void; onRowClick: (u: AdminUser) => void;
}) {
  const allChecked = users.length > 0 && users.every((u) => selected.has(u.id));
  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="w-10 px-3 py-2">
              <input type="checkbox" aria-label="Seleziona pagina" className="size-4"
                checked={allChecked} onChange={onTogglePage} />
            </th>
            {COLS.map((c) => (
              <th key={c.key} className="px-3 py-2">
                <button type="button" className="inline-flex items-center gap-1 hover:text-foreground"
                  onClick={() => onSort(c.key)}>
                  {c.label}
                  {sort === c.key && (order === "asc"
                    ? <ArrowUp className="size-3" /> : <ArrowDown className="size-3" />)}
                </button>
              </th>
            ))}
            <th className="px-3 py-2">Ruolo</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id} className="cursor-pointer border-t hover:bg-muted/30"
              onClick={() => onRowClick(u)}>
              <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                <input type="checkbox" aria-label={`Seleziona ${u.username}`} className="size-4"
                  checked={selected.has(u.id)}
                  onClick={(e) => onToggle(u.id, (e as unknown as MouseEvent).shiftKey)}
                  onChange={() => {}} />
              </td>
              <td className="px-3 py-2 font-medium">{u.username}</td>
              <td className="px-3 py-2 text-muted-foreground">{u.email}</td>
              <td className="px-3 py-2">
                <Badge variant={u.is_active ? "secondary" : "destructive"}>
                  {u.is_active ? "Attivo" : "Disattivato"}
                </Badge>
              </td>
              <td className="px-3 py-2">
                {u.is_admin
                  ? <Badge variant="secondary" className="gap-1"><ShieldCheck className="size-3" /> Admin</Badge>
                  : <span className="text-muted-foreground">Utente</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
