"use client";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Download, UserPlus } from "lucide-react";
import {
  me, adminListUsers, adminUsersStats, adminListGroups, adminBulkUsers, adminUsersCsvUrl,
  type AdminUser, type UsersFilters, type UsersStats, type BulkAction,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { UsersToolbar } from "@/components/admin/UsersToolbar";
import { UsersTable } from "@/components/admin/UsersTable";
import { BulkActionBar } from "@/components/admin/BulkActionBar";
import { UserEditSheet } from "@/components/admin/UserEditSheet";
import { AddUserSheet } from "@/components/admin/AddUserSheet";
import { ConfirmDialog } from "@/components/admin/ConfirmDialog";

type GroupOpt = { id: number; name: string };

export default function AdminUsers() {
  const router = useRouter();
  const [meId, setMeId] = useState<number | null>(null);
  const [groups, setGroups] = useState<GroupOpt[]>([]);
  const [stats, setStats] = useState<UsersStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const [filters, setFilters] = useState<UsersFilters>({});
  const [sort, setSort] = useState("username");
  const [order, setOrder] = useState("asc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [allMatching, setAllMatching] = useState(false);
  const [lastIdx, setLastIdx] = useState<number | null>(null);
  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [adding, setAdding] = useState(false);
  const [pendingBulk, setPendingBulk] = useState<null | { action: BulkAction; opts?: { group_id?: number | null; value?: boolean } }>(null);
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async () => {
    try {
      const res = await adminListUsers({ ...filters, sort, order, page, page_size: pageSize });
      setUsers(res.items); setTotal(res.total);
      adminUsersStats().then(setStats).catch(() => {});
    } catch {
      setNotice("Impossibile caricare gli utenti. Riprova.");
    } finally {
      setLoading(false);
    }
  }, [filters, sort, order, page, pageSize]);

  useEffect(() => { (async () => {
    const u = await me();
    if (!u || !u.is_admin) { router.replace("/"); return; }
    setMeId(u.id);
    setGroups(await adminListGroups());
  })(); }, [router]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [res, nextStats] = await Promise.all([
          adminListUsers({ ...filters, sort, order, page, page_size: pageSize }),
          adminUsersStats(),
        ]);
        if (cancelled) return;
        setUsers(res.items); setTotal(res.total); setStats(nextStats);
      } catch {
        if (!cancelled) setNotice("Impossibile caricare gli utenti. Riprova.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [filters, sort, order, page, pageSize]);

  useEffect(() => {
    if (!notice) return;
    const id = setTimeout(() => setNotice(""), 5000);
    return () => clearTimeout(id);
  }, [notice]);

  function clearSel() { setSelected(new Set()); setAllMatching(false); setLastIdx(null); }

  function toggle(id: number, shift: boolean) {
    const idx = users.findIndex((u) => u.id === id);
    setSelected((prev) => {
      const next = new Set(prev);
      if (shift && lastIdx !== null) {
        const [a, b] = [Math.min(lastIdx, idx), Math.max(lastIdx, idx)];
        for (let i = a; i <= b; i++) next.add(users[i].id);
      } else {
        if (next.has(id)) next.delete(id);
        else next.add(id);
      }
      return next;
    });
    setAllMatching(false); setLastIdx(idx);
  }
  function togglePage() {
    setAllMatching(false);
    setSelected((prev) => prev.size === users.length ? new Set() : new Set(users.map((u) => u.id)));
  }

  async function runBulk(action: BulkAction, opts?: { group_id?: number | null; value?: boolean }) {
    setLoading(true);
    const body = allMatching
      ? { action, all_matching: true, filters, ...opts }
      : { action, user_ids: [...selected], ...opts };
    const res = await adminBulkUsers(body);
    clearSel();
    const skipped = res.skipped.length ? ` · ${res.skipped.length} saltati (self/ultimo admin)` : "";
    setNotice(`${res.affected} utenti aggiornati${skipped}`);
    refresh();
  }

  function onAction(action: BulkAction, opts?: { group_id?: number | null; value?: boolean }) {
    if (action === "delete" || action === "set_admin") setPendingBulk({ action, opts });
    else runBulk(action, opts);
  }

  const pages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <main className="travel-map-pattern min-h-screen">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-6 md:py-10">
        <div className="flex items-center gap-3">
          <Button type="button" variant="outline" size="icon" aria-label="Indietro" onClick={() => router.push("/")}>
            <ArrowLeft aria-hidden />
          </Button>
          <div className="flex-1">
            <h1 className="text-2xl font-semibold">Gestione utenti</h1>
            {stats && <p className="text-sm text-muted-foreground">
              {stats.total} utenti · {stats.active} attivi · {stats.admins} admin · {stats.inactive} disattivati
            </p>}
          </div>
          <a href={adminUsersCsvUrl(filters)}>
            <Button variant="outline" className="gap-2"><Download aria-hidden className="size-4" /> CSV</Button>
          </a>
          <Button className="gap-2" onClick={() => setAdding(true)}><UserPlus aria-hidden className="size-4" /> Aggiungi</Button>
        </div>

        <Card>
          <CardContent className="flex flex-col gap-3 pt-4">
            <UsersToolbar filters={filters} groups={groups} pageSize={pageSize}
              onFilters={(f) => { setLoading(true); setFilters(f); setPage(1); clearSel(); }}
              onPageSize={(n) => { setLoading(true); setPageSize(n); setPage(1); }} />

            {notice && <p className="rounded-md bg-muted px-3 py-2 text-sm">{notice}</p>}

            {selected.size > 0 && (
              <BulkActionBar count={allMatching ? total : selected.size} total={total} allMatching={allMatching}
                groups={groups} onSelectAllMatching={() => setAllMatching(true)}
                onAction={onAction} onClear={clearSel} />
            )}

            {loading ? (
              <div className="flex flex-col gap-2">
                {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
              </div>
            ) : users.length === 0 ? (
              <p className="py-10 text-center text-sm text-muted-foreground">Nessun utente trovato.</p>
            ) : (
              <UsersTable users={users} selected={selected} sort={sort} order={order}
                onToggle={toggle} onTogglePage={togglePage}
                onSort={(c) => { setLoading(true); setOrder(sort === c && order === "asc" ? "desc" : "asc"); setSort(c); }}
                onRowClick={setEditing} />
            )}

            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>{total} utenti</span>
              <span className="flex items-center gap-2">
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => { setLoading(true); setPage((p) => p - 1); }}>‹</Button>
                Pag {page}/{pages}
                <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => { setLoading(true); setPage((p) => p + 1); }}>›</Button>
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      <UserEditSheet user={editing} groups={groups} canDelete={editing?.id !== meId}
        onClose={() => setEditing(null)} onSaved={refresh} />
      <AddUserSheet open={adding} onOpenChange={setAdding} onCreated={refresh} />
      <ConfirmDialog open={pendingBulk !== null}
        destructive={pendingBulk?.action === "delete"}
        confirmLabel={pendingBulk?.action === "delete" ? "Elimina" : "Conferma"}
        title={pendingBulk?.action === "delete"
          ? `Eliminare ${allMatching ? total : selected.size} utenti?`
          : `Aggiornare ${allMatching ? total : selected.size} utenti?`}
        description={pendingBulk?.action === "delete"
          ? "Cancella anche chat e dati collegati. Irreversibile. Il tuo account e l'ultimo admin sono protetti."
          : undefined}
        onConfirm={() => { if (pendingBulk) runBulk(pendingBulk.action, pendingBulk.opts); }}
        onOpenChange={(o) => { if (!o) setPendingBulk(null); }} />
    </main>
  );
}
