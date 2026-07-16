"use client";
import { Button } from "@/components/ui/button";
import type { BulkAction } from "@/lib/api";

type GroupOpt = { id: number; name: string };

export function BulkActionBar({ count, total, allMatching, groups, onSelectAllMatching, onAction, onClear }: {
  count: number; total: number; allMatching: boolean; groups: GroupOpt[];
  onSelectAllMatching: () => void; onAction: (a: BulkAction, o?: { group_id?: number; value?: boolean }) => void;
  onClear: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-muted/40 px-3 py-2 text-sm">
      <span className="font-medium">
        {allMatching ? `Tutti i ${total} selezionati` : `${count} selezionati`}
      </span>
      {count > 0 && !allMatching && (
        <Button variant="link" size="sm" onClick={onSelectAllMatching}>
          Seleziona tutti i {total} risultati
        </Button>
      )}
      <span className="mx-1 h-5 w-px bg-border" />
      <Button variant="outline" size="sm" onClick={() => onAction("activate")}>Attiva</Button>
      <Button variant="outline" size="sm" onClick={() => onAction("deactivate")}>Disattiva</Button>
      <select aria-label="Assegna gruppo" className="h-8 rounded-lg border border-input bg-background px-2 text-sm"
        defaultValue="" onChange={(e) => { if (e.target.value) onAction("set_group", { group_id: Number(e.target.value) }); e.target.value = ""; }}>
        <option value="" disabled>Assegna gruppo…</option>
        {groups.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
      </select>
      <Button variant="outline" size="sm" onClick={() => onAction("set_admin", { value: true })}>Rendi admin</Button>
      <Button variant="outline" size="sm" onClick={() => onAction("set_admin", { value: false })}>Revoca admin</Button>
      <Button variant="destructive" size="sm" onClick={() => onAction("delete")}>Elimina</Button>
      <Button variant="ghost" size="sm" onClick={onClear}>Annulla</Button>
    </div>
  );
}
