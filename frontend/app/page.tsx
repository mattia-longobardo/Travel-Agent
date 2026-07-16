"use client";
import { useEffect, useRef, useState } from "react";
import { useIsMobile } from "@/lib/useIsMobile";
import { MobileConsole } from "@/components/mobile/MobileConsole";
import {
  Archive,
  BriefcaseBusiness,
  FileSpreadsheet,
  FolderPlus,
  MessageSquare,
  MoreVertical,
  Plus,
  Share2,
  Trash2,
  Upload,
} from "lucide-react";
import { useChat } from "@/lib/useChat";
import {
  me, listChats, createChat, getChat, getMessages, patchChat, deleteChat,
  listChatGroups, createChatGroup, renameChatGroup, deleteChatGroup,
  setChatStatus, moveChatToGroup, emptyTrash,
} from "@/lib/api";
import { AgentTimeline } from "@/components/AgentTimeline";
import { TypingBubble } from "@/components/TypingBubble";
import { QuestionChips } from "@/components/QuestionChips";
import { PackageCarousel } from "@/components/PackageCarousel";
import { LocationSelector } from "@/components/LocationSelector";
import { groupByLocation, type LocationGroup } from "@/lib/grouping";
import { EmptyState } from "@/components/EmptyState";
import { ChatComposer } from "@/components/ChatComposer";
import { AccountMenu } from "@/components/AccountMenu";
import { BriefPanel } from "@/components/BriefPanel";
import { ChatRow } from "@/components/ChatRow";
import { TravelMark } from "@/components/Brand";
import { ShareDialog } from "@/components/ShareDialog";
import { GroupDialog } from "@/components/GroupDialog";
import { NameDialog } from "@/components/NameDialog";
import { exportPackagesXlsx } from "@/lib/excel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { AccommodationType, BriefData, ChatGroup, ChatSummary, ChatTitleEvent, Me, PackageCardData, QuestionEvent, ResultBatch, SearchMode, View, Tab, ChatActions } from "@/lib/types";
import { MessageBubble } from "@/components/MessageBubble";
import { ResultsPanel } from "@/components/ResultsPanel";
import { ResultBatchSelector } from "@/components/ResultBatchSelector";
import { exportMarkdown } from "@/lib/exportMarkdown";

function GroupHeader({ group, onRename, onDelete }: {
  group: ChatGroup; onRename: (g: ChatGroup) => void; onDelete: (id: number) => void;
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
    <div ref={ref} className="relative mt-3 flex items-center justify-between px-2">
      <span className="truncate text-xs font-semibold uppercase tracking-wide text-muted-foreground">{group.name}</span>
      <button type="button" aria-label={`Azioni gruppo ${group.name}`} onClick={() => setOpen((o) => !o)} className="rounded-md p-1 text-muted-foreground hover:bg-accent">
        <MoreVertical aria-hidden className="size-4" />
      </button>
      {open && (
        <div role="menu" className="absolute right-0 top-8 z-20 w-44 rounded-lg border bg-popover p-1 shadow-lg">
          <button className={item} onClick={() => { setOpen(false); onRename(group); }}>Rinomina gruppo</button>
          <button className={item + " text-destructive"} onClick={() => { setOpen(false); onDelete(group.id); }}>Elimina gruppo</button>
        </div>
      )}
    </div>
  );
}

function ViewTab({ active, label, icon: Icon, onClick }: { active: boolean; label: string; icon: typeof Archive; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick}
      className={"flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition " + (active ? "bg-primary/10 text-primary font-medium" : "text-muted-foreground hover:bg-sidebar-accent")}>
      <Icon aria-hidden className="size-4" /> {label}
    </button>
  );
}

function AppSidebar({ user, chats, groups, view, activeChatId, actions, onNew, onView, onNewGroup, onRenameGroup, onDeleteGroup, onEmptyTrash }: {
  user: Me | null;
  chats: ChatSummary[];
  groups: ChatGroup[];
  view: View;
  activeChatId: number | null;
  actions: ChatActions;
  onNew: () => void;
  onView: (v: View) => void;
  onNewGroup: () => void;
  onRenameGroup: (g: ChatGroup) => void;
  onDeleteGroup: (id: number) => void;
  onEmptyTrash: () => void;
}) {
  const row = (chat: ChatSummary) => (
    <ChatRow key={chat.id} chat={chat} active={chat.id === activeChatId} groups={groups}
      onSelect={actions.onSelect} onArchive={actions.onArchive} onTrash={actions.onTrash}
      onRestore={actions.onRestore} onDeleteForever={actions.onDeleteForever}
      onShare={actions.onShare} onMove={actions.onMove} onRename={actions.onRename} />
  );
  const ungrouped = chats.filter((c) => !c.chat_group_id);
  return (
    <aside className="hidden h-full min-h-0 border-r bg-sidebar/80 px-5 py-4 lg:flex lg:flex-col">
      <div className="flex items-center gap-3">
        <TravelMark />
        <div className="min-w-0">
          <div className="text-lg font-semibold leading-tight">Travel Agent</div>
          <div className="text-xs text-muted-foreground">{user?.username ?? "—"}</div>
        </div>
      </div>

      <Button className="mt-7 h-10 justify-start gap-2" size="lg" onClick={onNew}>
        <Plus data-icon="inline-start" aria-hidden="true" />
        Nuovo viaggio
      </Button>

      <div className="mt-8 flex items-center justify-between">
        <h2 className="text-sm font-semibold">
          {view === "active" ? "Chat" : view === "archived" ? "Archivio" : "Cestino"}
        </h2>
        {view === "active" && (
          <Button type="button" variant="ghost" size="icon-sm" aria-label="Nuovo gruppo" onClick={onNewGroup}>
            <FolderPlus aria-hidden="true" />
          </Button>
        )}
      </div>

      {view === "trashed" && chats.length > 0 && (
        <Button type="button" variant="outline" size="sm" className="mt-3 justify-start gap-2 text-destructive" onClick={onEmptyTrash}>
          <Trash2 aria-hidden="true" className="size-4" /> Svuota cestino
        </Button>
      )}

      <nav className="mt-3 flex flex-1 flex-col gap-1 overflow-y-auto">
        {chats.length === 0 && (
          <p className="px-2 py-2 text-xs text-muted-foreground">Nessuna chat qui.</p>
        )}
        {view === "active" ? (
          <>
            {groups.map((g) => {
              const inGroup = chats.filter((c) => c.chat_group_id === g.id);
              return (
                <div key={g.id}>
                  <GroupHeader group={g} onRename={onRenameGroup} onDelete={onDeleteGroup} />
                  {inGroup.length === 0
                    ? <p className="px-2 py-1 text-xs text-muted-foreground/70">vuoto</p>
                    : inGroup.map(row)}
                </div>
              );
            })}
            {groups.length > 0 && ungrouped.length > 0 && (
              <div className="mt-3 px-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Senza gruppo</div>
            )}
            {ungrouped.map(row)}
          </>
        ) : (
          chats.map(row)
        )}
      </nav>

      <div className="mt-4 flex flex-col gap-1 border-t pt-3">
        <ViewTab active={view === "active"} label="Chat" icon={MessageSquare} onClick={() => onView("active")} />
        <ViewTab active={view === "archived"} label="Archivio" icon={Archive} onClick={() => onView("archived")} />
        <ViewTab active={view === "trashed"} label="Cestino" icon={Trash2} onClick={() => onView("trashed")} />
      </div>

      <AccountMenu user={user} />
    </aside>
  );
}

function ShellHeader({ title, hasActive, onShare, onExport, onRename, onArchive, onTrash }: {
  title: string; hasActive: boolean;
  onShare: () => void; onExport: () => void; onRename: () => void; onArchive: () => void; onTrash: () => void;
}) {
  const [menu, setMenu] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    function h(e: MouseEvent) { if (ref.current && !ref.current.contains(e.target as Node)) setMenu(false); }
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);
  const item = "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent";
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b bg-background/90 px-4 backdrop-blur md:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <div className="lg:hidden">
          <TravelMark />
        </div>
        <div className="min-w-0">
          <h1 className="truncate text-base font-semibold md:text-lg">{title}</h1>
          <p className="hidden text-xs text-muted-foreground sm:block">
            Chat viaggio con timeline agenti e pacchetti in tempo reale
          </p>
        </div>
      </div>

      <div ref={ref} className="relative flex items-center gap-2">
        <Button type="button" variant="outline" size="icon" aria-label="Condividi" disabled={!hasActive} onClick={onShare}>
          <Share2 aria-hidden="true" />
        </Button>
        <Button type="button" variant="outline" size="icon" aria-label="Esporta" disabled={!hasActive} onClick={onExport}>
          <Upload aria-hidden="true" />
        </Button>
        <Button type="button" variant="ghost" size="icon" aria-label="Menu" aria-haspopup="menu" aria-expanded={menu}
          disabled={!hasActive} onClick={() => setMenu((m) => !m)}>
          <MoreVertical aria-hidden="true" />
        </Button>
        {menu && (
          <div role="menu" className="absolute right-0 top-12 z-20 w-48 rounded-lg border bg-popover p-1 shadow-lg">
            <button className={item} onClick={() => { setMenu(false); onRename(); }}>Rinomina</button>
            <button className={item} onClick={() => { setMenu(false); onArchive(); }}>Archivia</button>
            <button className={item + " text-destructive"} onClick={() => { setMenu(false); onTrash(); }}>Sposta nel cestino</button>
          </div>
        )}
      </div>
    </header>
  );
}

function InsightRail({ brief, packages, resultBatches, selectedResultBatchId, onSelectResultBatch, groups, selectedLocation, onSelectLocation, tab, onTab, searchMode }: {
  brief: BriefData | null;
  packages: PackageCardData[];
  resultBatches: ResultBatch[];
  selectedResultBatchId: string | null;
  onSelectResultBatch: (id: string) => void;
  groups: LocationGroup[];
  selectedLocation: string | null;
  onSelectLocation: (key: string) => void;
  tab: Tab;
  onTab: (t: Tab) => void;
  searchMode?: SearchMode;
}) {
  const tabClass = (active: boolean) =>
    active
      ? "rounded-md bg-background px-2 py-1.5 text-primary shadow-sm"
      : "rounded-md px-2 py-1.5 text-muted-foreground";

  return (
    <aside className="hidden h-full min-h-0 border-l bg-background/90 px-5 py-4 xl:flex xl:flex-col xl:gap-4">
      <div className="grid shrink-0 grid-cols-2 rounded-lg bg-muted p-1 text-sm font-medium">
        <button type="button" className={tabClass(tab === "brief")} onClick={() => onTab("brief")}>
          Brief viaggio
        </button>
        <button type="button" className={tabClass(tab === "risultati")} onClick={() => onTab("risultati")}>
          Risultati
        </button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        {tab === "brief" && <BriefPanel brief={brief} />}
        {tab === "risultati" && (
          <ResultsPanel
            packages={packages}
            groups={groups}
            selectedLocation={selectedLocation}
            onSelectLocation={onSelectLocation}
            searchMode={searchMode}
            resultBatches={resultBatches}
            selectedResultBatchId={selectedResultBatchId}
            onSelectResultBatch={onSelectResultBatch}
          />
        )}
      </div>
    </aside>
  );
}

export default function Page() {
  const [user, setUser] = useState<Me | null>(null);
  const [chats, setChats] = useState<ChatSummary[]>([]);
  const [groups, setGroups] = useState<ChatGroup[]>([]);
  const [view, setView] = useState<View>("active");
  const [activeChatId, setActiveChatId] = useState<number | null>(null);
  const [tab, setTab] = useState<Tab>("brief");
  const [draft, setDraft] = useState("");
  const [shareTarget, setShareTarget] = useState<number | null>(null);
  const [groupDialog, setGroupDialog] = useState<{ open: boolean; mode: "create" | "rename"; id?: number; initial?: string }>({ open: false, mode: "create" });
  const [renameTarget, setRenameTarget] = useState<number | null>(null);
  // Shared between the chat results area and the sidebar "Risultati" panel: which
  // location's cards are shown when results span more than one destination.
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null);
  const [searchMode, setSearchMode] = useState<SearchMode>("flight_hotel");
  const [accommodationType, setAccommodationType] = useState<AccommodationType>("both");

  const isMobile = useIsMobile();

  const {
    steps,
    packages,
    resultBatches,
    selectedResultBatchId,
    selectResultBatch,
    question,
    messages,
    brief,
    error,
    sending,
    send,
    cancel,
    hydrate,
    reset,
    setSending,
  } =
    useChat(activeChatId ?? 0);
  // Id of a chat we just lazily created on first send: the hydrate effect skips it so the
  // optimistic user message + live stream aren't clobbered by re-fetching empty server state.
  const pendingNewChatRef = useRef<number | null>(null);

  async function refreshChats(v: View = view) { setChats((await listChats(v)).sort((a, b) => b.id - a.id)); }
  async function refreshGroups() { setGroups(await listChatGroups()); }

  // Bootstrap: identity + groups + chat list. With no chats we stay in a draft "new trip"
  // state (no chat is created) — the chat is created lazily on the first sent message so empty,
  // never-used chats never appear in the sidebar.
  useEffect(() => {
    (async () => {
      const [u, list, grps] = await Promise.all([me(), listChats("active"), listChatGroups()]);
      setUser(u);
      setGroups(grps);
      const sorted = [...list].sort((a, b) => b.id - a.id);
      setChats(sorted);
      if (sorted.length) {
        setActiveChatId(sorted[0].id);
      }
    })();
  }, []);

  function applyChatTitle(chatTitle: ChatTitleEvent) {
    setChats((cs) => cs.map((c) => (
      c.id === chatTitle.chat_id ? { ...c, title: chatTitle.title } : c
    )));
  }

  // Reload chats whenever the view (active/archived/trashed) changes.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const next = (await listChats(view)).sort((a, b) => b.id - a.id);
      if (!cancelled) setChats(next);
    })();
    return () => { cancelled = true; };
  }, [view]);

  // Hydrate the view from history whenever the active chat changes. If a search is still
  // running server-side (e.g. the user reloaded the page mid-search), resume it: the backend
  // run is detached from the request and persists its result, so we show the working state
  // and poll until the run clears, then render the result instead of leaving the user on an
  // idle screen that looks like the search was lost.
  useEffect(() => {
    if (!activeChatId) return;
    // Skip a chat we just created locally on first send — there is nothing to hydrate and
    // re-fetching would wipe the optimistic message and the in-flight stream.
    if (pendingNewChatRef.current === activeChatId) { pendingNewChatRef.current = null; return; }
    const id = activeChatId;
    let cancelled = false;

    // Keys in params_json that are run control, not part of the trip brief.
    const CONTROL_KEYS = new Set(["pending_question", "run_active"]);

    async function loadOnce() {
      const [chat, msgs] = await Promise.all([getChat(id), getMessages(id)]);
      if (cancelled) return chat;
      const bubbles = msgs
        .filter((m) => m.role === "user" || m.role === "assistant")
        .map((m) => ({ role: m.role as "user" | "assistant", content: m.content, created_at: m.created_at }));
      const batches: ResultBatch[] = msgs
        .filter((m) => m.role === "assistant" && (m.tool_calls_json?.ranked?.length ?? 0) > 0)
        .map((m) => ({
          id: `message-${m.id}`,
          packages: m.tool_calls_json?.ranked ?? [],
          created_at: m.created_at,
        }));
      const params = chat.params_json ?? {};
      const hasBrief = Object.keys(params).some((k) => !CONTROL_KEYS.has(k));
      const pendingQuestion = (params.pending_question as QuestionEvent | null | undefined) ?? null;
      hydrate({
        messages: bubbles,
        resultBatches: batches,
        brief: hasBrief ? (params as unknown as BriefData) : null,
        question: pendingQuestion,
      });
      return chat;
    }

    (async () => {
      let chat = await loadOnce();
      if (cancelled || !chat.params_json?.run_active) return;
      // A run is in progress server-side — show the working state and poll until it ends,
      // then re-hydrate to display the persisted result. Capped so a crashed/stale run
      // (marker never cleared) eventually stops polling.
      setSending(true);
      const startedAt = Date.now();
      while (!cancelled && chat.params_json?.run_active && Date.now() - startedAt < 5 * 60_000) {
        await new Promise((r) => setTimeout(r, 2500));
        if (cancelled) break;
        try { chat = await getChat(id); } catch { break; }
      }
      if (!cancelled) await loadOnce(); // final hydrate also resets `sending` to false
    })();

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeChatId]);

  // Start a fresh trip as a draft: no chat is created until the first message is sent.
  function newTrip() {
    setView("active");
    reset();
    setActiveChatId(null);
    setDraft("");
    setSearchMode("flight_hotel");
    setAccommodationType("both");
  }

  async function handleSend(
    text: string,
    answerTo?: string,
    opts?: { generateMore?: boolean; refineText?: string },
  ) {
    // Allow an empty `text` only for the "just propose more options" action.
    if (!text.trim() && !opts?.generateMore) return;
    let id = activeChatId;
    if (id == null) {
      // Lazy-create the chat on the first message of a draft "new trip".
      const c = await createChat();
      pendingNewChatRef.current = c.id;
      setChats((cs) => [c, ...cs]);
      setActiveChatId(c.id);
      id = c.id;
    }
    const streamOpts = {
      ...(opts ?? {}),
      searchMode: brief?.search_mode ?? searchMode,
      accommodationType: brief?.accommodation_type ?? accommodationType,
      onChatTitle: applyChatTitle,
    };
    await send(text, answerTo, id, streamOpts);
  }

  const actions: ChatActions = {
    onSelect: setActiveChatId,
    onArchive: async (id) => { await setChatStatus(id, "archived"); await refreshChats(); },
    onTrash: async (id) => {
      await setChatStatus(id, "trashed");
      // Moving a chat to the trash closes it if it is the one currently open.
      if (id === activeChatId) { reset(); setActiveChatId(null); }
      await refreshChats();
    },
    onRestore: async (id) => { await setChatStatus(id, "active"); await refreshChats(); },
    onDeleteForever: async (id) => {
      await deleteChat(id);
      // Stay in the current view (the trash) and just drop the row; only close the
      // reading pane if the deleted chat was the one open in it.
      if (id === activeChatId) { reset(); setActiveChatId(null); }
      await refreshChats();
    },
    onShare: (id) => setShareTarget(id),
    onMove: async (id, gid) => { await moveChatToGroup(id, gid); await refreshChats(); },
    onRename: (id) => setRenameTarget(id),
  };

  async function submitGroup(name: string) {
    if (groupDialog.mode === "create") await createChatGroup(name);
    else if (groupDialog.id != null) await renameChatGroup(groupDialog.id, name);
    await refreshGroups();
  }
  async function removeGroup(id: number) {
    await deleteChatGroup(id);
    await Promise.all([refreshGroups(), refreshChats()]);
  }
  async function onEmptyTrash() {
    if (chats.length === 0) return;
    // If the chat open in the reading pane is one of the trashed ones being purged,
    // close it — otherwise leave the open (non-trashed) chat untouched.
    const closingActive = activeChatId !== null && chats.some((c) => c.id === activeChatId);
    await emptyTrash();
    if (closingActive) { reset(); setActiveChatId(null); }
    // Stay in the trash; it is now empty (the "Svuota cestino" button hides itself).
    await refreshChats();
  }
  async function renameChat(title: string) {
    if (renameTarget == null) return;
    const updated = await patchChat(renameTarget, { title });
    setChats((cs) => cs.map((c) => (c.id === updated.id ? { ...c, title: updated.title } : c)));
  }

  const activeChat = chats.find((c) => c.id === activeChatId);
  const renameChat_ = chats.find((c) => c.id === renameTarget);
  const empty = messages.length === 0 && !sending;

  // Group the (already ranked) packages by location. The selector + active-group
  // logic only kicks in when results span more than one destination.
  const locationGroups = groupByLocation(packages);
  const resolvedLocation = locationGroups.some((g) => g.key === selectedLocation)
    ? selectedLocation
    : locationGroups[0]?.key ?? null;
  const activeGroup =
    locationGroups.find((g) => g.key === resolvedLocation) ?? null;
  // Cards shown in the chat carousel: the active location's up-to-10 when grouped,
  // otherwise the full ranked list (single location → unchanged behaviour).
  const chatItems = (locationGroups.length > 1 ? (activeGroup?.items ?? []) : packages).slice(0, 10);
  const effectiveSearchMode = brief?.search_mode ?? searchMode;
  const effectiveAccommodationType = brief?.accommodation_type ?? accommodationType;
  const resultTitle = effectiveSearchMode === "flight_only"
    ? "Voli"
    : effectiveSearchMode === "hotel_only"
      ? "Alloggi"
      : "Volo + hotel";
  const composerPlaceholder = effectiveSearchMode === "flight_only"
    ? "Descrivi destinazione, date e budget del volo..."
    : effectiveSearchMode === "hotel_only"
      ? "Descrivi destinazione, date e budget del soggiorno..."
      : "Descrivi date, budget e stile del viaggio...";

  return (
    <main className="h-dvh overflow-hidden bg-background text-foreground">
      {isMobile ? (
        <MobileConsole
          key={activeChatId ?? "new-trip"}
          user={user}
          chats={chats}
          groups={groups}
          view={view}
          activeChatId={activeChatId}
          actions={actions}
          onNew={newTrip}
          onView={setView}
          onEmptyTrash={onEmptyTrash}
          title={activeChat?.title ?? "Nuovo viaggio"}
          hasActive={activeChatId !== null}
          onShare={() => activeChatId !== null && setShareTarget(activeChatId)}
          onExport={() => exportMarkdown(activeChat?.title ?? "viaggio", messages, packages)}
          onRename={() => activeChatId !== null && setRenameTarget(activeChatId)}
          onArchive={() => activeChatId !== null && actions.onArchive(activeChatId)}
          onTrash={() => activeChatId !== null && actions.onTrash(activeChatId)}
          messages={messages}
          sending={sending}
          onStop={cancel}
          steps={steps}
          error={error}
          question={question}
          draft={draft}
          setDraft={setDraft}
          handleSend={handleSend}
          onPickEmpty={setDraft}
          searchMode={effectiveSearchMode}
          accommodationType={effectiveAccommodationType}
          onSearchModeChange={setSearchMode}
          onAccommodationTypeChange={setAccommodationType}
          brief={brief}
          packages={packages}
          resultBatches={resultBatches}
          selectedResultBatchId={selectedResultBatchId}
          onSelectResultBatch={selectResultBatch}
          chatItems={chatItems}
          locationGroups={locationGroups}
          selectedLocation={activeGroup?.key ?? null}
          onSelectLocation={setSelectedLocation}
          onExportExcel={() => exportPackagesXlsx(activeChat?.title ?? "viaggio", packages)}
        />
      ) : (
        <div className="grid h-full lg:grid-cols-[20rem_minmax(0,1fr)] xl:grid-cols-[20rem_minmax(0,1fr)_25rem]">
          <AppSidebar
            user={user}
            chats={chats}
            groups={groups}
            view={view}
            activeChatId={activeChatId}
            actions={actions}
            onNew={newTrip}
            onView={setView}
            onNewGroup={() => setGroupDialog({ open: true, mode: "create" })}
            onRenameGroup={(g) => setGroupDialog({ open: true, mode: "rename", id: g.id, initial: g.name })}
            onDeleteGroup={removeGroup}
            onEmptyTrash={onEmptyTrash}
          />
          <section className="flex h-full min-h-0 min-w-0 flex-col">
            <ShellHeader
              title={activeChat?.title ?? "Nuovo viaggio"}
              hasActive={activeChatId !== null}
              onShare={() => activeChatId !== null && setShareTarget(activeChatId)}
              onExport={() => exportMarkdown(activeChat?.title ?? "viaggio", messages, packages)}
              onRename={() => activeChatId !== null && setRenameTarget(activeChatId)}
              onArchive={() => activeChatId !== null && actions.onArchive(activeChatId)}
              onTrash={() => activeChatId !== null && actions.onTrash(activeChatId)}
            />
            <div className="travel-map-pattern min-h-0 flex-1 overflow-y-auto">
              <div className="mx-auto flex w-full max-w-5xl flex-col px-4 py-6 md:px-8">
                <div className="flex flex-1 flex-col gap-6">
                  {empty && (
                    <EmptyState
                      onPick={setDraft}
                      mode={effectiveSearchMode}
                      accommodationType={effectiveAccommodationType}
                      onModeChange={setSearchMode}
                      onAccommodationTypeChange={setAccommodationType}
                    />
                  )}
                  {messages.map((m, i) => (
                    <MessageBubble key={`${m.role}-${i}`} role={m.role} content={m.content} createdAt={m.created_at} />
                  ))}
                  {sending && (
                    <>
                      <TypingBubble />
                      <section className="rounded-lg border bg-card p-4 shadow-sm">
                        <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
                          <BriefcaseBusiness aria-hidden="true" />
                          Agenti al lavoro
                        </div>
                        <AgentTimeline steps={steps} />
                      </section>
                    </>
                  )}
                  {packages.length > 0 && (
                    <section className="flex flex-col gap-3">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <h2 className="text-base font-semibold">{resultTitle}</h2>
                          <p className="text-sm text-muted-foreground">
                            Pacchetti ordinati per valore e vincoli del brief.
                          </p>
                        </div>
                        <div className="flex shrink-0 items-center gap-2">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="gap-2"
                            onClick={() => exportPackagesXlsx(activeChat?.title ?? "viaggio", packages)}
                          >
                            <FileSpreadsheet aria-hidden="true" className="size-4" />
                            Esporta Excel
                          </Button>
                          <Badge variant="secondary">
                            {locationGroups.length > 1
                              ? `${chatItems.length} di ${packages.length} opzioni`
                              : `${packages.length} opzioni`}
                          </Badge>
                        </div>
                      </div>
                      <ResultBatchSelector
                        batches={resultBatches}
                        selectedId={selectedResultBatchId}
                        onSelect={selectResultBatch}
                      />
                      {locationGroups.length > 1 && activeGroup && (
                        <LocationSelector
                          groups={locationGroups}
                          selected={activeGroup.key}
                          onSelect={setSelectedLocation}
                        />
                      )}
                      <PackageCarousel items={chatItems} />
                    </section>
                  )}
                  {question && (
                    <QuestionChips
                      q={question}
                      onAnswer={(v, opts) => handleSend(String(v), question.id, opts)}
                    />
                  )}
                </div>
                {error && (
                  <div className="mt-4 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-2 text-sm text-destructive">
                    {error}
                  </div>
                )}
              </div>
            </div>
            <div className="shrink-0 border-t bg-background/95 backdrop-blur">
              <div className="mx-auto w-full max-w-5xl px-4 py-3 md:px-8">
                <ChatComposer
                  value={draft}
                  onChange={setDraft}
                  onSend={() => {
                    const t = draft;
                    setDraft("");
                    handleSend(t);
                  }}
                  disabled={sending}
                  sending={sending}
                  onStop={cancel}
                  placeholder={composerPlaceholder}
                />
              </div>
            </div>
          </section>
          <InsightRail
            brief={brief}
            packages={packages}
            resultBatches={resultBatches}
            selectedResultBatchId={selectedResultBatchId}
            onSelectResultBatch={selectResultBatch}
            groups={locationGroups}
            selectedLocation={activeGroup?.key ?? null}
            onSelectLocation={setSelectedLocation}
            tab={tab}
            onTab={setTab}
            searchMode={effectiveSearchMode}
          />
        </div>
      )}
      <ShareDialog chatId={shareTarget} open={shareTarget !== null} onClose={() => setShareTarget(null)} />
      <GroupDialog
        open={groupDialog.open}
        mode={groupDialog.mode}
        initial={groupDialog.initial}
        onSubmit={submitGroup}
        onClose={() => setGroupDialog((g) => ({ ...g, open: false }))}
      />
      <NameDialog
        open={renameTarget !== null}
        title="Rinomina chat"
        placeholder="Titolo della chat"
        initial={renameChat_?.title}
        onSubmit={renameChat}
        onClose={() => setRenameTarget(null)}
      />
    </main>
  );
}
