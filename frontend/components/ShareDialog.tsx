"use client";
import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { shareChat } from "@/lib/api";

export function ShareDialog({ chatId, open, onClose }: { chatId: number | null; open: boolean; onClose: () => void }) {
  const [email, setEmail] = useState("");
  const [perm, setPerm] = useState<"read" | "write">("read");
  const [err, setErr] = useState("");
  const [ok, setOk] = useState(false);
  async function submit() {
    if (!chatId) return;
    setErr(""); setOk(false);
    try { await shareChat(chatId, email, perm); setOk(true); setEmail(""); }
    catch { setErr("Impossibile condividere (utente non trovato?)"); }
  }
  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) { onClose(); setErr(""); setOk(false); } }}>
      <DialogContent>
        <DialogHeader><DialogTitle>Condividi chat</DialogTitle></DialogHeader>
        <div className="flex flex-col gap-3">
          <Input placeholder="email utente" value={email} onChange={(e) => setEmail(e.target.value)} />
          <select className="rounded-md border bg-background px-2 py-2 text-sm" value={perm} onChange={(e) => setPerm(e.target.value as "read" | "write")}>
            <option value="read">Lettura</option>
            <option value="write">Scrittura</option>
          </select>
          {err && <p className="text-sm text-destructive">{err}</p>}
          {ok && <p className="text-sm text-primary">Condivisa.</p>}
        </div>
        <DialogFooter><Button onClick={submit}>Condividi</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
