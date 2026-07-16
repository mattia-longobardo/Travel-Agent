"use client";
import { useState } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetFooter } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { adminCreateUser } from "@/lib/api";

export function AddUserSheet({ open, onOpenChange, onCreated }: {
  open: boolean; onOpenChange: (o: boolean) => void; onCreated: () => void;
}) {
  const [nu, setNu] = useState(""); const [ne, setNe] = useState("");
  const [np, setNp] = useState(""); const [admin, setAdmin] = useState(false);
  const [err, setErr] = useState("");

  async function add() {
    if (!nu.trim() || !ne.trim() || !np.trim()) { setErr("Compila nome utente, email e password."); return; }
    setErr("");
    try {
      await adminCreateUser({ username: nu.trim(), email: ne.trim(), password: np, is_admin: admin });
      setNu(""); setNe(""); setNp(""); setAdmin(false);
      onCreated(); onOpenChange(false);
    } catch { setErr("Impossibile creare l'utente (nome o email già in uso?)."); }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-md">
        <SheetHeader><SheetTitle>Aggiungi utente</SheetTitle></SheetHeader>
        <div className="flex flex-1 flex-col gap-3 px-4">
          {err && <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{err}</p>}
          <Input placeholder="Nome utente" value={nu} onChange={(e) => setNu(e.target.value)} />
          <Input placeholder="Email" type="email" value={ne} onChange={(e) => setNe(e.target.value)} />
          <Input placeholder="Password" type="password" value={np} onChange={(e) => setNp(e.target.value)} />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" className="size-4" checked={admin} onChange={(e) => setAdmin(e.target.checked)} /> Amministratore
          </label>
        </div>
        <SheetFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Annulla</Button>
          <Button onClick={add}>Aggiungi</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
