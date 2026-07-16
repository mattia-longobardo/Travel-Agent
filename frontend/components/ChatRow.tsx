"use client";
import { useEffect, useRef, useState } from "react";
import { MessageCircle, MoreVertical } from "lucide-react";
import type { ChatGroup, ChatSummary } from "@/lib/types";

export function ChatRow({ chat, active, groups, onSelect, onArchive, onTrash, onRestore, onDeleteForever, onShare, onMove, onRename }: {
  chat: ChatSummary; active: boolean; groups: ChatGroup[];
  onSelect: (id: number) => void; onArchive: (id: number) => void; onTrash: (id: number) => void;
  onRestore: (id: number) => void; onDeleteForever: (id: number) => void;
  onShare: (id: number) => void; onMove: (id: number, gid: number | null) => void;
  onRename: (id: number) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    function h(e: MouseEvent) { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); }
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);
  const item = "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent";
  return (
    <div ref={ref} className="group relative grid grid-cols-[2rem_minmax(0,1fr)_auto] items-center gap-2 rounded-lg px-2 py-2 transition hover:bg-sidebar-accent data-[active=true]:bg-primary/10" data-active={active || undefined}>
      <span className="grid size-8 place-items-center rounded-lg bg-background text-muted-foreground ring-1 ring-border group-data-[active=true]:bg-primary group-data-[active=true]:text-primary-foreground"><MessageCircle aria-hidden /></span>
      <button type="button" onClick={() => onSelect(chat.id)} className="min-w-0 text-left">
        <span className="block truncate text-sm font-medium">{chat.title}</span>
      </button>
      <button type="button" aria-label="Azioni chat" onClick={() => setOpen((o) => !o)} className="rounded-md p-1 text-muted-foreground hover:bg-accent"><MoreVertical aria-hidden className="size-4" /></button>
      {open && (
        <div role="menu" className="absolute right-0 top-10 z-20 w-52 rounded-lg border bg-popover p-1 shadow-lg">
          {chat.status === "active" && <>
            <button className={item} onClick={() => { setOpen(false); onRename(chat.id); }}>Rinomina</button>
            <button className={item} onClick={() => { setOpen(false); onShare(chat.id); }}>Condividi</button>
            <button className={item} onClick={() => { setOpen(false); onArchive(chat.id); }}>Archivia</button>
            {groups.length > 0 && <>
              <div className="px-2 py-1 text-xs text-muted-foreground">Sposta nel gruppo</div>
              <button className={item} onClick={() => { setOpen(false); onMove(chat.id, null); }}>Senza gruppo</button>
              {groups.map((g) => <button key={g.id} className={item} onClick={() => { setOpen(false); onMove(chat.id, g.id); }}>{g.name}</button>)}
            </>}
            <button className={item + " text-destructive"} onClick={() => { setOpen(false); onTrash(chat.id); }}>Sposta nel cestino</button>
          </>}
          {chat.status === "archived" && <>
            <button className={item} onClick={() => { setOpen(false); onRestore(chat.id); }}>Ripristina</button>
            <button className={item + " text-destructive"} onClick={() => { setOpen(false); onTrash(chat.id); }}>Sposta nel cestino</button>
          </>}
          {chat.status === "trashed" && <>
            <button className={item} onClick={() => { setOpen(false); onRestore(chat.id); }}>Ripristina</button>
            <button className={item + " text-destructive"} onClick={() => { setOpen(false); onDeleteForever(chat.id); }}>Elimina definitivamente</button>
          </>}
        </div>
      )}
    </div>
  );
}
