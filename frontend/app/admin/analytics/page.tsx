"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, ArrowLeft, BarChart3, Download, RefreshCw, Search } from "lucide-react";
import {
  me, adminOverview, adminPaths, adminModels, adminChats, adminAnalyticsOwners, adminChatsCsvUrl,
} from "@/lib/api";
import type { AnalyticsOverview, AnalyticsPath, AnalyticsChatRow, ModelsResult, AnalyticsOwner } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { TimeRangeSelector } from "@/components/admin/TimeRangeSelector";
import { AnalyticsTimeChart } from "@/components/admin/AnalyticsTimeChart";
import { AnalyticsCostChart } from "@/components/admin/AnalyticsCostChart";
import { AnalyticsPathChart } from "@/components/admin/AnalyticsPathChart";
import { ModelBreakdownTable } from "@/components/admin/ModelBreakdownTable";
import { ChatsAnalyticsTable } from "@/components/admin/ChatsAnalyticsTable";

const fmtNum = (n: number) => (n ?? 0).toLocaleString("it-IT");
const fmtLat = (ms: number) => (!ms ? "0 ms" : ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)} ms`);
const fmtUsd = (n: number) => `$${n.toFixed(n < 0.01 ? 6 : 2)}`;

function Kpi({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <Card>
      <CardContent className="flex h-full min-h-28 flex-col gap-1 py-5 text-left">
        <span className="text-sm text-muted-foreground">{label}</span>
        <span className="text-2xl font-semibold">{value}</span>
        {sub && <span className="mt-auto text-xs text-muted-foreground">{sub}</span>}
      </CardContent>
    </Card>
  );
}

function ErrorNotice({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="alert" className="flex flex-wrap items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm">
      <AlertCircle aria-hidden className="size-4 text-destructive" />
      <span className="min-w-0 flex-1">{message}</span>
      <Button type="button" variant="outline" size="sm" className="gap-2" onClick={onRetry}>
        <RefreshCw aria-hidden className="size-3.5" /> Riprova
      </Button>
    </div>
  );
}

export default function AdminAnalytics() {
  const router = useRouter();
  const [authorized, setAuthorized] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [range, setRange] = useState("30d");
  const [userId, setUserId] = useState<number | "">("");
  const selectedUserId = userId === "" ? undefined : userId;

  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [paths, setPaths] = useState<AnalyticsPath[]>([]);
  const [models, setModels] = useState<ModelsResult | null>(null);
  const [owners, setOwners] = useState<AnalyticsOwner[]>([]);
  const [loadingDashboard, setLoadingDashboard] = useState(true);
  const [dashboardError, setDashboardError] = useState<string | null>(null);

  const [rows, setRows] = useState<AnalyticsChatRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loadingChats, setLoadingChats] = useState(true);
  const [chatsError, setChatsError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [sort, setSort] = useState("created_at");
  const [order, setOrder] = useState("desc");
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const dashboardRequest = useRef(0);
  const chatsRequest = useRef(0);

  const loadIdentity = useCallback(async () => {
    setAuthError(null);
    try {
      const user = await me();
      if (!user || !user.is_admin) {
        router.replace("/");
        return;
      }
      setAuthorized(true);
      setOwners(await adminAnalyticsOwners());
    } catch {
      setAuthError("Non è stato possibile verificare l’accesso o caricare i proprietari delle chat.");
    }
  }, [router]);

  useEffect(() => {
    const timeout = window.setTimeout(() => { void loadIdentity(); }, 0);
    return () => window.clearTimeout(timeout);
  }, [loadIdentity]);

  const loadDashboard = useCallback(async () => {
    const requestId = ++dashboardRequest.current;
    setLoadingDashboard(true);
    setDashboardError(null);
    setOverview(null);
    setPaths([]);
    setModels(null);
    try {
      const [nextOverview, nextPaths, nextModels] = await Promise.all([
        adminOverview(range, selectedUserId),
        adminPaths(range, selectedUserId),
        adminModels(range, selectedUserId),
      ]);
      if (requestId !== dashboardRequest.current) return;
      setOverview(nextOverview);
      setPaths(nextPaths.paths);
      setModels(nextModels);
    } catch {
      if (requestId === dashboardRequest.current) {
        setDashboardError("Le metriche non sono disponibili in questo momento.");
      }
    } finally {
      if (requestId === dashboardRequest.current) setLoadingDashboard(false);
    }
  }, [range, selectedUserId]);

  useEffect(() => {
    if (!authorized) return;
    const timeout = window.setTimeout(() => { void loadDashboard(); }, 0);
    return () => window.clearTimeout(timeout);
  }, [authorized, loadDashboard]);

  const refreshChats = useCallback(async () => {
    const requestId = ++chatsRequest.current;
    setLoadingChats(true);
    setChatsError(null);
    setRows([]);
    setTotal(0);
    try {
      const res = await adminChats({
        q: q || undefined,
        user_id: selectedUserId,
        range,
        sort,
        order,
        page,
        page_size: pageSize,
      });
      if (requestId !== chatsRequest.current) return;
      setRows(res.items);
      setTotal(res.total);
    } catch {
      if (requestId === chatsRequest.current) setChatsError("Non è stato possibile caricare le chat.");
    } finally {
      if (requestId === chatsRequest.current) setLoadingChats(false);
    }
  }, [q, selectedUserId, range, sort, order, page]);

  useEffect(() => {
    if (!authorized) return;
    const timeout = window.setTimeout(() => { void refreshChats(); }, 0);
    return () => window.clearTimeout(timeout);
  }, [authorized, refreshChats]);

  function clearDashboard() {
    dashboardRequest.current += 1;
    setOverview(null);
    setPaths([]);
    setModels(null);
    setDashboardError(null);
    setLoadingDashboard(true);
  }

  function clearChats() {
    chatsRequest.current += 1;
    setRows([]);
    setTotal(0);
    setChatsError(null);
    setLoadingChats(true);
  }

  function toggleSort(col: string) {
    clearChats();
    if (sort === col) setOrder((value) => (value === "asc" ? "desc" : "asc"));
    else { setSort(col); setOrder("desc"); }
    setPage(1);
  }

  function selectRange(nextRange: string) {
    if (nextRange === range) return;
    clearDashboard();
    clearChats();
    setRange(nextRange);
    setPage(1);
  }

  function selectUser(value: string) {
    const nextUserId = value === "" ? "" : Number(value);
    if (nextUserId === userId) return;
    clearDashboard();
    clearChats();
    setUserId(nextUserId);
    setPage(1);
  }

  function openErrors() {
    const params = new URLSearchParams({ range });
    if (selectedUserId != null) params.set("user_id", String(selectedUserId));
    router.push(`/admin/analytics/errors?${params.toString()}`);
  }

  const csvFilters = { q: q || undefined, user_id: selectedUserId, range, sort, order };
  const pages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <main className="travel-map-pattern min-h-screen">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6 md:py-10">
        <div className="flex flex-wrap items-center gap-3">
          <Button type="button" variant="outline" size="icon" aria-label="Indietro" onClick={() => router.push("/")}>
            <ArrowLeft aria-hidden="true" />
          </Button>
          <div className="min-w-56 flex-1">
            <h1 className="text-2xl font-semibold">Analytics</h1>
            <p className="text-sm text-muted-foreground">Attività, affidabilità, costi e percorsi del sistema.</p>
          </div>
          <select
            aria-label="Proprietario chat"
            className="h-9 rounded-md border bg-background px-2 text-sm"
            value={userId}
            onChange={(event) => selectUser(event.target.value)}
          >
            <option value="">Tutti i proprietari</option>
            {owners.map((owner) => <option key={owner.id} value={owner.id}>{owner.username}</option>)}
          </select>
          <TimeRangeSelector value={range} onChange={selectRange} />
        </div>

        {authError && <ErrorNotice message={authError} onRetry={() => void loadIdentity()} />}
        {dashboardError && <ErrorNotice message={dashboardError} onRetry={() => void loadDashboard()} />}

        {loadingDashboard && !overview ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-28 w-full" />)}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            <Kpi label="Run" value={fmtNum(overview?.total_runs ?? 0)} sub={`${fmtNum(overview?.total_messages ?? 0)} messaggi`} />
            <Kpi label="Chat create o attive" value={fmtNum(overview?.total_chats ?? 0)} sub={`${fmtNum(overview?.total_users ?? 0)} proprietari nel periodo`} />
            <Kpi
              label="Successo"
              value={`${((overview?.success_rate ?? 0) * 100).toFixed(1)}%`}
              sub={`${fmtNum(overview?.total_successes ?? 0)} ok · ${fmtNum(overview?.total_errors ?? 0)} errori · ${fmtNum(overview?.total_cancelled ?? 0)} annullati`}
            />
            <Kpi label="Latenza media" value={fmtLat(overview?.avg_latency_ms ?? 0)} sub="per run" />
            <Kpi
              label="Costo stimato"
              value={fmtUsd(overview?.estimated_cost_usd ?? 0)}
              sub={overview?.has_unpriced ? "Parziale: tariffa non nota per alcuni run" : "USD nel periodo"}
            />
            <Kpi
              label="Token"
              value={fmtNum(overview?.total_tokens ?? 0)}
              sub={`${fmtNum(overview?.total_prompt_tokens ?? 0)} in · ${fmtNum(overview?.total_completion_tokens ?? 0)} out`}
            />
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-[3fr_2fr]">
          <Card>
            <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>Esiti giornalieri</CardTitle>
                <p className="mt-1 text-xs text-muted-foreground">Le interruzioni utente sono separate dagli errori tecnici.</p>
              </div>
              <Button type="button" variant="outline" size="sm" onClick={openErrors}>Dettaglio errori</Button>
            </CardHeader>
            <CardContent>
              {loadingDashboard && !overview ? <Skeleton className="h-64 w-full" /> : <AnalyticsTimeChart data={overview?.by_day ?? []} />}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Costo giornaliero</CardTitle>
              <p className="text-xs text-muted-foreground">Passa sul grafico per vedere costo, copertura tariffaria e token.</p>
            </CardHeader>
            <CardContent>
              {loadingDashboard && !overview ? <Skeleton className="h-52 w-full" /> : <AnalyticsCostChart data={overview?.by_day ?? []} />}
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><BarChart3 aria-hidden className="size-5" /> Percorsi più usati</CardTitle>
              <p className="text-xs text-muted-foreground">I rami di ricerca eseguiti in parallelo sono riuniti nello stesso percorso logico.</p>
            </CardHeader>
            <CardContent>{loadingDashboard && !overview ? <Skeleton className="h-40 w-full" /> : <AnalyticsPathChart paths={paths} />}</CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Modelli e costi</CardTitle></CardHeader>
            <CardContent>{models ? <ModelBreakdownTable data={models} /> : <Skeleton className="h-40 w-full" />}</CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle>Chat nel periodo</CardTitle>
              <p className="mt-1 text-xs text-muted-foreground">Include chat create o con attività nel periodo selezionato.</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative">
                <Search aria-hidden className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  className="h-9 w-48 pl-8"
                  placeholder="Cerca titolo/proprietario…"
                  value={q}
                  onChange={(event) => { clearChats(); setQ(event.target.value); setPage(1); }}
                />
              </div>
              <a href={adminChatsCsvUrl(csvFilters)}>
                <Button variant="outline" size="sm" className="gap-2"><Download aria-hidden className="size-4" /> CSV</Button>
              </a>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {chatsError && <ErrorNotice message={chatsError} onRetry={() => void refreshChats()} />}
            {loadingChats ? <Skeleton className="h-40 w-full" />
              : <ChatsAnalyticsTable rows={rows} range={range} sort={sort} order={order} onSort={toggleSort} />}
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>{fmtNum(total)} chat</span>
              <span className="flex items-center gap-2">
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => { clearChats(); setPage((value) => value - 1); }}>‹</Button>
                Pag {page}/{pages}
                <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => { clearChats(); setPage((value) => value + 1); }}>›</Button>
              </span>
            </div>
          </CardContent>
        </Card>

        <p className="text-xs text-muted-foreground">
          Click sui risultati e prenotazioni completate non sono ancora tracciati; questa vista misura l’attività interna del sistema.
        </p>
      </div>
    </main>
  );
}
