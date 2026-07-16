"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertCircle, ArrowLeft, RefreshCw } from "lucide-react";
import { me, adminErrors, adminModels } from "@/lib/api";
import type { AnalyticsErrorRow, ModelsResult } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { TimeRangeSelector } from "@/components/admin/TimeRangeSelector";
import { ErrorsTable } from "@/components/admin/ErrorsTable";

function ErrorNotice({ message, retryLabel, onRetry }: {
  message: string;
  retryLabel: string;
  onRetry: () => void;
}) {
  return (
    <div role="alert" className="flex flex-wrap items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm">
      <AlertCircle aria-hidden className="size-4 text-destructive" />
      <span className="min-w-0 flex-1">{message}</span>
      <Button type="button" variant="outline" size="sm" className="gap-2" onClick={onRetry}>
        <RefreshCw aria-hidden className="size-3.5" /> {retryLabel}
      </Button>
    </div>
  );
}

function ErrorsContent() {
  const router = useRouter();
  const sp = useSearchParams();
  const queryUserId = Number(sp.get("user_id"));
  const userId = Number.isInteger(queryUserId) && queryUserId > 0 ? queryUserId : undefined;
  const queryPage = Number(sp.get("page"));
  const [range, setRange] = useState(sp.get("range") || "30d");
  const [model, setModel] = useState(sp.get("model") || "");
  const [page, setPage] = useState(Number.isInteger(queryPage) && queryPage > 0 ? queryPage : 1);
  const pageSize = 50;
  const [authorized, setAuthorized] = useState(false);
  const [items, setItems] = useState<AnalyticsErrorRow[]>([]);
  const [total, setTotal] = useState(0);
  const [models, setModels] = useState<ModelsResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingModels, setLoadingModels] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const [errorsError, setErrorsError] = useState<string | null>(null);
  const modelsRequest = useRef(0);
  const errorsRequest = useRef(0);

  const loadIdentity = useCallback(async () => {
    setAuthError(null);
    try {
      const user = await me();
      if (!user || !user.is_admin) { router.replace("/"); return; }
      setAuthorized(true);
    } catch {
      setAuthError("Non è stato possibile verificare l’accesso.");
    }
  }, [router]);

  useEffect(() => {
    const timeout = window.setTimeout(() => { void loadIdentity(); }, 0);
    return () => window.clearTimeout(timeout);
  }, [loadIdentity]);

  const loadModels = useCallback(async () => {
    const requestId = ++modelsRequest.current;
    setModels(null);
    setLoadingModels(true);
    setModelsError(null);
    try {
      const result = await adminModels(range, userId);
      if (requestId === modelsRequest.current) setModels(result);
    } catch {
      if (requestId === modelsRequest.current) {
        setModelsError("Non è stato possibile caricare i filtri dei modelli.");
      }
    } finally {
      if (requestId === modelsRequest.current) setLoadingModels(false);
    }
  }, [range, userId]);

  const loadErrors = useCallback(async () => {
    const requestId = ++errorsRequest.current;
    setLoading(true);
    setItems([]);
    setTotal(0);
    setErrorsError(null);
    try {
      const res = await adminErrors({ range, model: model || undefined, user_id: userId, page, page_size: pageSize });
      if (requestId !== errorsRequest.current) return;
      setItems(res.items);
      setTotal(res.total);
    } catch {
      if (requestId === errorsRequest.current) {
        setErrorsError("Non è stato possibile caricare gli errori tecnici.");
      }
    } finally {
      if (requestId === errorsRequest.current) setLoading(false);
    }
  }, [range, model, userId, page]);

  useEffect(() => {
    if (!authorized) return;
    const timeout = window.setTimeout(() => { void loadModels(); }, 0);
    return () => window.clearTimeout(timeout);
  }, [authorized, loadModels]);

  useEffect(() => {
    if (!authorized) return;
    const timeout = window.setTimeout(() => { void loadErrors(); }, 0);
    return () => window.clearTimeout(timeout);
  }, [authorized, loadErrors]);

  function clearModels() {
    modelsRequest.current += 1;
    setModels(null);
    setModelsError(null);
    setLoadingModels(true);
  }

  function clearErrors() {
    errorsRequest.current += 1;
    setItems([]);
    setTotal(0);
    setErrorsError(null);
    setLoading(true);
  }

  function selectRange(value: string) {
    if (value === range) return;
    clearModels();
    clearErrors();
    setRange(value);
    setPage(1);
  }

  function selectModel(value: string) {
    if (value === model) return;
    clearErrors();
    setModel(value);
    setPage(1);
  }

  function changePage(nextPage: number) {
    if (nextPage === page) return;
    clearErrors();
    setPage(nextPage);
  }

  const pages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <main className="travel-map-pattern min-h-screen">
      <div className="mx-auto flex max-w-5xl flex-col gap-6 px-4 py-6 md:py-10">
        <div className="flex flex-wrap items-center gap-3">
          <Button type="button" variant="outline" size="icon" aria-label="Indietro" onClick={() => router.back()}>
            <ArrowLeft aria-hidden="true" />
          </Button>
          <div className="flex-1">
            <h1 className="text-2xl font-semibold">Errori tecnici</h1>
            <p className="text-sm text-muted-foreground">Le esecuzioni annullate dall’utente non sono conteggiate come errori.</p>
          </div>
          <TimeRangeSelector value={range} onChange={selectRange} />
        </div>

        {authError && <ErrorNotice message={authError} retryLabel="Riprova accesso" onRetry={() => void loadIdentity()} />}
        {modelsError && <ErrorNotice message={modelsError} retryLabel="Riprova modelli" onRetry={() => void loadModels()} />}
        {errorsError && <ErrorNotice message={errorsError} retryLabel="Riprova errori" onRetry={() => void loadErrors()} />}

        <Card>
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3">
            <CardTitle>{errorsError ? "Errori non disponibili" : `${total} errori`}</CardTitle>
            <select
              aria-label="Filtra per modello"
              className="h-9 rounded-md border bg-background px-2 text-sm"
              value={model}
              disabled={loadingModels || modelsError != null}
              onChange={(event) => selectModel(event.target.value)}
            >
              <option value="">{loadingModels ? "Caricamento modelli…" : "Tutti i modelli"}</option>
              {model && !(models?.items ?? []).some((item) => item.model === model) && <option value={model}>{model}</option>}
              {(models?.items ?? []).map((item) => <option key={item.model ?? "—"} value={item.model ?? ""}>{item.model ?? "—"}</option>)}
            </select>
          </CardHeader>
          <CardContent>
            {loading ? <Skeleton className="h-40 w-full" /> : errorsError ? (
              <p className="py-10 text-center text-sm text-muted-foreground">Dati degli errori non disponibili.</p>
            ) : <ErrorsTable items={items} range={range} />}
            <div className="mt-3 flex items-center justify-end gap-2 text-sm text-muted-foreground">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => changePage(page - 1)}>‹</Button>
              Pag {page}/{pages}
              <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => changePage(page + 1)}>›</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}

export default function AdminErrors() {
  return (
    <Suspense fallback={<main className="travel-map-pattern min-h-screen"><div className="p-10 text-center text-sm text-muted-foreground">Caricamento…</div></main>}>
      <ErrorsContent />
    </Suspense>
  );
}
