"use client";
import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

function GroupDialogForm({ mode, initial, onSubmit, onClose }: {
  mode: "create" | "rename"; initial?: string;
  onSubmit: (name: string) => void; onClose: () => void;
}) {
  const [name, setName] = useState(initial ?? "");
  return (
    <>
      <DialogHeader><DialogTitle>{mode === "create" ? "Nuovo gruppo" : "Rinomina gruppo"}</DialogTitle></DialogHeader>
      <Input placeholder="Nome gruppo" value={name} onChange={(e) => setName(e.target.value)} />
      <DialogFooter><Button onClick={() => { if (name.trim()) { onSubmit(name.trim()); onClose(); } }}>Salva</Button></DialogFooter>
    </>
  );
}

export function GroupDialog({ open, mode, initial, onSubmit, onClose }: {
  open: boolean; mode: "create" | "rename"; initial?: string;
  onSubmit: (name: string) => void; onClose: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      {open && (
        <DialogContent>
          <GroupDialogForm
            key={`${mode}:${initial ?? ""}`}
            mode={mode}
            initial={initial}
            onSubmit={onSubmit}
            onClose={onClose}
          />
        </DialogContent>
      )}
    </Dialog>
  );
}
