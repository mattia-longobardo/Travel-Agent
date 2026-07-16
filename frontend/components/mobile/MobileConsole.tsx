"use client";
import { useEffect, useRef, useState } from "react";
import { ArrowRight, BriefcaseBusiness, FileSpreadsheet, Menu, MoreVertical, Share2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MobileTabBar, type MobileTab } from "@/components/mobile/MobileTabBar";
import { MobileDrawer } from "@/components/mobile/MobileDrawer";
import { MessageBubble } from "@/components/MessageBubble";
import { BriefPanel } from "@/components/BriefPanel";
import { AgentTimeline } from "@/components/AgentTimeline";
import { TypingBubble } from "@/components/TypingBubble";
import { QuestionChips } from "@/components/QuestionChips";
import { EmptyState } from "@/components/EmptyState";
import { ChatComposer } from "@/components/ChatComposer";
import { Logo } from "@/components/Logo";
import { MobilePackageCard } from "@/components/mobile/MobilePackageCard";
import { LocationSelector } from "@/components/LocationSelector";
import { ResultBatchSelector } from "@/components/ResultBatchSelector";
import type { ChatMsg } from "@/lib/useChat";
import type { LocationGroup } from "@/lib/grouping";
import type {
  AccommodationType, AgentStep, BriefData, ChatActions, ChatGroup, ChatSummary, Me, PackageCardData, QuestionEvent, ResultBatch, SearchMode, View,
} from "@/lib/types";

export interface MobileConsoleProps {
  // navigazione / drawer
  user: Me | null;
  chats: ChatSummary[];
  groups: ChatGroup[];
  view: View;
  activeChatId: number | null;
  actions: ChatActions;
  onNew: () => void;
  onView: (v: View) => void;
  onEmptyTrash: () => void;
  // header
  title: string;
  hasActive: boolean;
  onShare: () => void;
  onExport: () => void;
  onRename: () => void;
  onArchive: () => void;
  onTrash: () => void;
  // chat view
  messages: ChatMsg[];
  sending: boolean;
  onStop: () => void;
  steps: AgentStep[];
  error: string | null;
  question: QuestionEvent | null;
  draft: string;
  setDraft: (v: string) => void;
  handleSend: (text: string, answerTo?: string,
               opts?: { generateMore?: boolean; refineText?: string }) => void;
  onPickEmpty: (t: string) => void;
  searchMode: SearchMode;
  accommodationType: AccommodationType;
  onSearchModeChange: (mode: SearchMode) => void;
  onAccommodationTypeChange: (type: AccommodationType) => void;
  // brief view
  brief: BriefData | null;
  // results view
  packages: PackageCardData[];
  resultBatches: ResultBatch[];
  selectedResultBatchId: string | null;
  onSelectResultBatch: (id: string) => void;
  chatItems: PackageCardData[];
  locationGroups: LocationGroup[];
  selectedLocation: string | null;
  onSelectLocation: (key: string) => void;
  onExportExcel: () => void;
}

export function MobileConsole(props: MobileConsoleProps) {
  const [tab, setTab] = useState<MobileTab>("chat");
  const [drawer, setDrawer] = useState(false);
  const [menu, setMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const empty = props.messages.length === 0 && !props.sending;

  // Close header menu on outside click or Escape
  useEffect(() => {
    function onMouseDown(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenu(false);
      }
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setMenu(false);
    }
    document.addEventListener("mousedown", onMouseDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onMouseDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Header */}
      <header className="flex min-h-14 shrink-0 items-center justify-between border-b bg-background/90 px-3 pt-[env(safe-area-inset-top)] backdrop-blur">
        <div className="flex min-w-0 items-center gap-2">
          <Button type="button" variant="ghost" size="icon" aria-label="Apri menu" onClick={() => setDrawer(true)}>
            <Menu aria-hidden="true" />
          </Button>
          <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-primary text-primary-foreground">
            <Logo className="size-5" />
          </span>
          <h1 className="truncate text-base font-semibold">{props.title}</h1>
        </div>
        <div ref={menuRef} className="relative flex items-center">
          <Button type="button" variant="ghost" size="icon" aria-label="Azioni"
            disabled={!props.hasActive} aria-haspopup="menu" aria-expanded={menu}
            onClick={() => setMenu((m) => !m)}>
            <MoreVertical aria-hidden="true" />
          </Button>
          {menu && (
            <div role="menu" className="absolute right-0 top-12 z-30 w-52 rounded-lg border bg-popover p-1 shadow-lg">
              <button className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm hover:bg-accent" onClick={() => { setMenu(false); props.onShare(); }}><Share2 className="size-4" /> Condividi</button>
              <button className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm hover:bg-accent" onClick={() => { setMenu(false); props.onExport(); }}><Upload className="size-4" /> Esporta Markdown</button>
              <button className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm hover:bg-accent" onClick={() => { setMenu(false); props.onRename(); }}>Rinomina</button>
              <button className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm hover:bg-accent" onClick={() => { setMenu(false); props.onArchive(); }}>Archivia</button>
              <button className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm text-destructive hover:bg-accent" onClick={() => { setMenu(false); props.onTrash(); }}>Sposta nel cestino</button>
            </div>
          )}
        </div>
      </header>

      {/* Contenuto */}
      <div className="travel-map-pattern min-h-0 flex-1 overflow-y-auto">
        {tab === "chat" && (
          <div className="flex flex-col gap-5 px-4 py-4">
            {empty && (
              <EmptyState
                onPick={props.onPickEmpty}
                mode={props.searchMode}
                accommodationType={props.accommodationType}
                onModeChange={props.onSearchModeChange}
                onAccommodationTypeChange={props.onAccommodationTypeChange}
              />
            )}
            {props.messages.map((m, i) => (
              <MessageBubble key={`${m.role}-${i}`} role={m.role} content={m.content} createdAt={m.created_at} />
            ))}
            {props.sending && (
              <>
                <TypingBubble />
                <section className="rounded-lg border bg-card p-4 shadow-sm">
                  <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
                    <BriefcaseBusiness aria-hidden="true" /> Agenti al lavoro
                  </div>
                  <AgentTimeline steps={props.steps} />
                </section>
              </>
            )}
            {props.question && (
              <QuestionChips q={props.question} onAnswer={(v, opts) => props.handleSend(String(v), props.question!.id, opts)} />
            )}
            {props.error && (
              <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-2 text-sm text-destructive">{props.error}</div>
            )}
            {props.packages.length > 0 && (
              <button
                type="button"
                onClick={() => setTab("risultati")}
                className="sticky bottom-2 flex min-h-12 w-full items-center justify-between rounded-xl bg-primary px-4 text-left text-sm font-semibold text-primary-foreground shadow-lg"
              >
                <span>Vedi {props.packages.length} {props.packages.length === 1 ? "risultato" : "risultati"}</span>
                <ArrowRight aria-hidden="true" className="size-5" />
              </button>
            )}
          </div>
        )}

        {tab === "brief" && (
          <div className="px-4 py-5"><BriefPanel brief={props.brief} /></div>
        )}

        {tab === "risultati" && (
          <div className="flex flex-col gap-3 px-4 py-4">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold">
                  {props.searchMode === "flight_only" ? "Voli" : props.searchMode === "hotel_only" ? "Alloggi" : "Volo + hotel"}
                </h2>
                {props.packages.length > 0 && (
                  <Badge variant="secondary">
                    {props.locationGroups.length > 1
                      ? `${props.chatItems.length} di ${props.packages.length} opzioni`
                      : `${props.packages.length} opzioni`}
                  </Badge>
                )}
              </div>
              {props.packages.length > 0 && (
                <Button type="button" variant="outline" size="sm" className="gap-2" onClick={props.onExportExcel}>
                  <FileSpreadsheet aria-hidden="true" className="size-4" /> Excel
                </Button>
              )}
            </div>
            <ResultBatchSelector
              batches={props.resultBatches}
              selectedId={props.selectedResultBatchId}
              onSelect={props.onSelectResultBatch}
            />
            {props.packages.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">Nessun risultato ancora.</p>
            ) : (
              <>
                {props.locationGroups.length > 1 && props.selectedLocation && (
                  <LocationSelector
                    groups={props.locationGroups}
                    selected={props.selectedLocation}
                    onSelect={props.onSelectLocation}
                  />
                )}
                <div className="flex flex-col gap-3">
                  {props.chatItems.map((p) => (
                    <MobilePackageCard key={p.id} data={p} />
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Composer: solo sul tab Chat */}
      {tab === "chat" && (
        <div className="shrink-0 border-t bg-background/95 px-3 py-2 backdrop-blur">
          <ChatComposer
            value={props.draft}
            onChange={props.setDraft}
            onSend={() => { const t = props.draft; props.setDraft(""); props.handleSend(t); }}
            disabled={props.sending}
            sending={props.sending}
            onStop={props.onStop}
            placeholder={props.searchMode === "flight_only"
              ? "Descrivi destinazione, date e budget del volo..."
              : props.searchMode === "hotel_only"
                ? "Descrivi destinazione, date e budget del soggiorno..."
                : "Descrivi date, budget e stile del viaggio..."}
          />
        </div>
      )}

      <MobileTabBar active={tab} onTab={setTab} resultCount={props.packages.length} />

      <MobileDrawer
        open={drawer} onClose={() => setDrawer(false)}
        user={props.user} chats={props.chats} groups={props.groups} view={props.view}
        activeChatId={props.activeChatId} actions={props.actions}
        onNew={props.onNew} onView={props.onView} onEmptyTrash={props.onEmptyTrash}
      />
    </div>
  );
}
