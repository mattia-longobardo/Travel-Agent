"use client";
import { useState } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetFooter } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ConfirmDialog } from "@/components/admin/ConfirmDialog";
import { adminUpdateUser, adminDeleteUser, type AdminUser } from "@/lib/api";

type GroupOpt = { id: number; name: string };

function UserEditForm({ user, groups, canDelete, onClose, onSaved }: {
  user: AdminUser; groups: GroupOpt[]; canDelete: boolean;
  onClose: () => void; onSaved: () => void;
}) {
  const [username, setUsername] = useState(user.username);
  const [email, setEmail] = useState(user.email);
  const [groupId, setGroupId] = useState<number | null>(user.group_id);
  const [isAdmin, setIsAdmin] = useState(user.is_admin);
  const [isActive, setIsActive] = useState(user.is_active);
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  const [confirm, setConfirm] = useState(false);

  async function save() {
    const body: Record<string, unknown> = {};
    if (username.trim() && username !== user.username) body.username = username.trim();
    if (email.trim() && email !== user.email) body.email = email.trim();
    if (groupId !== user.group_id) body.group_id = groupId;
    if (isAdmin !== user.is_admin) body.is_admin = isAdmin;
    if (isActive !== user.is_active) body.is_active = isActive;
    if (pw) body.password = pw;
    setErr("");
    try { await adminUpdateUser(user.id, body); onSaved(); onClose(); }
    catch { setErr("Impossibile salvare (nome/email in uso, o ultimo admin)."); }
  }

  async function doDelete() {
    try { await adminDeleteUser(user.id); onSaved(); onClose(); }
    catch { setErr("Impossibile eliminare l'utente."); }
  }

  return (
    <>
      <SheetHeader><SheetTitle>Modifica utente</SheetTitle></SheetHeader>
      <div className="flex flex-1 flex-col gap-3 overflow-y-auto px-4">
        {err && <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{err}</p>}
        <label className="text-sm">Username
          <Input aria-label="Username" value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label className="text-sm">Email
          <Input aria-label="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="text-sm">Gruppo
          <select className="mt-1 h-9 w-full rounded-lg border border-input bg-background px-2 text-sm"
            value={groupId ?? ""} onChange={(e) => setGroupId(e.target.value ? Number(e.target.value) : null)}>
            <option value="">—</option>
            {groups.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" className="size-4" checked={isAdmin} onChange={(e) => setIsAdmin(e.target.checked)} /> Amministratore
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" className="size-4" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} /> Attivo
        </label>
        <label className="text-sm">Nuova password
          <Input type="password" aria-label="Nuova password" placeholder="lascia vuoto per non cambiare"
            value={pw} onChange={(e) => setPw(e.target.value)} />
        </label>
        {canDelete && (
          <Button variant="destructive" className="mt-2 w-fit" onClick={() => setConfirm(true)}>
            Elimina utente
          </Button>
        )}
      </div>
      <SheetFooter>
        <Button variant="outline" onClick={onClose}>Annulla</Button>
        <Button onClick={save}>Salva</Button>
      </SheetFooter>
      <ConfirmDialog open={confirm} destructive confirmLabel="Elimina"
        title={`Eliminare "${user.username}"?`}
        description="Verranno cancellate anche tutte le sue chat e i dati collegati. Irreversibile."
        onConfirm={doDelete} onOpenChange={setConfirm} />
    </>
  );
}

export function UserEditSheet({ user, groups, canDelete, onClose, onSaved }: {
  user: AdminUser | null; groups: GroupOpt[]; canDelete: boolean;
  onClose: () => void; onSaved: () => void;
}) {
  return (
    <Sheet open={user != null} onOpenChange={(o) => { if (!o) onClose(); }}>
      <SheetContent side="right" className="w-full sm:max-w-md">
        {user && (
          <UserEditForm
            key={user.id}
            user={user}
            groups={groups}
            canDelete={canDelete}
            onClose={onClose}
            onSaved={onSaved}
          />
        )}
      </SheetContent>
    </Sheet>
  );
}
