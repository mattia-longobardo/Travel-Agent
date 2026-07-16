"use client";
import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

function NameDialogForm({ title, placeholder, initial, onSubmit, onClose }: {
  title: string; placeholder: string; initial?: string;
  onSubmit: (name: string) => void; onClose: () => void;
}) {
  const [name, setName] = useState(initial ?? "");
  return (
    <>
      <DialogHeader><DialogTitle>{title}</DialogTitle></DialogHeader>
      <Input placeholder={placeholder} value={name} onChange={(e) => setName(e.target.value)} />
      <DialogFooter><Button onClick={() => { if (name.trim()) { onSubmit(name.trim()); onClose(); } }}>Salva</Button></DialogFooter>
    </>
  );
}

export function NameDialog({ open, title, placeholder, initial, onSubmit, onClose }: {
  open: boolean; title: string; placeholder: string; initial?: string;
  onSubmit: (name: string) => void; onClose: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      {open && (
        <DialogContent>
          <NameDialogForm
            key={`${title}:${initial ?? ""}`}
            title={title}
            placeholder={placeholder}
            initial={initial}
            onSubmit={onSubmit}
            onClose={onClose}
          />
        </DialogContent>
      )}
    </Dialog>
  );
}
