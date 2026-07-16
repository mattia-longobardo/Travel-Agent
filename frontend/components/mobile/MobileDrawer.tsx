"use client";
import { Archive, MessageSquare, Plus, Trash2 } from "lucide-react";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { ChatRow } from "@/components/ChatRow";
import { AccountMenu } from "@/components/AccountMenu";
import type { ChatActions, ChatGroup, ChatSummary, Me, View } from "@/lib/types";

export function MobileDrawer({
  open, onClose, user, chats, groups, view, activeChatId, actions, onNew, onView, onEmptyTrash,
}: {
  open: boolean;
  onClose: () => void;
  user: Me | null;
  chats: ChatSummary[];
  groups: ChatGroup[];
  view: View;
  activeChatId: number | null;
  actions: ChatActions;
  onNew: () => void;
  onView: (v: View) => void;
  onEmptyTrash: () => void;
}) {
  // Wrap each action handler so selecting a chat / triggering an action also closes the drawer.
  const close = onClose;
  const selectAndClose = (id: number) => { actions.onSelect(id); close(); };
  const rowActions: ChatActions = { ...actions, onSelect: selectAndClose };

  const viewBtn = (v: View, label: string, Icon: typeof Archive) => (
    <button
      key={v}
      type="button"
      onClick={() => { onView(v); close(); }}
      className={"flex items-center gap-2 rounded-md px-2 py-2 text-sm " + (view === v ? "bg-primary/10 font-medium text-primary" : "text-muted-foreground hover:bg-accent")}
    >
      <Icon aria-hidden="true" className="size-4" /> {label}
    </button>
  );

  const ungrouped = chats.filter((c) => !c.chat_group_id);
  const row = (chat: ChatSummary) => (
    <ChatRow
      key={chat.id} chat={chat} active={chat.id === activeChatId} groups={groups}
      onSelect={rowActions.onSelect} onArchive={rowActions.onArchive} onTrash={rowActions.onTrash}
      onRestore={rowActions.onRestore} onDeleteForever={rowActions.onDeleteForever}
      onShare={rowActions.onShare} onMove={rowActions.onMove} onRename={rowActions.onRename}
    />
  );

  return (
    <Sheet open={open} onOpenChange={(o: boolean) => { if (!o) close(); }}>
      <SheetContent side="left" className="w-[88%] max-w-sm gap-0 p-0 sm:max-w-sm">
        <div className="flex h-full min-h-0 flex-col px-4 py-4">
          <SheetTitle className="px-1">Travel Agent</SheetTitle>

          <Button className="mt-4 h-11 justify-start gap-2" onClick={() => { onNew(); close(); }}>
            <Plus aria-hidden="true" /> Nuovo viaggio
          </Button>

          <h2 className="mt-5 px-1 text-sm font-semibold">
            {view === "active" ? "Chat" : view === "archived" ? "Archivio" : "Cestino"}
          </h2>

          {view === "trashed" && chats.length > 0 && (
            <Button variant="outline" size="sm" className="mt-2 justify-start gap-2 text-destructive"
              onClick={() => { onEmptyTrash(); close(); }}>
              <Trash2 aria-hidden="true" className="size-4" /> Svuota cestino
            </Button>
          )}

          <nav className="mt-2 flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
            {chats.length === 0 && <p className="px-2 py-2 text-xs text-muted-foreground">Nessuna chat qui.</p>}
            {view === "active"
              ? (<>
                  {groups.map((g) => {
                    const inGroup = chats.filter((c) => c.chat_group_id === g.id);
                    return (
                      <div key={g.id}>
                        <div className="mt-3 px-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{g.name}</div>
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
                </>)
              : chats.map(row)}
          </nav>

          <div className="mt-3 flex flex-col gap-1 border-t pt-3">
            {viewBtn("active", "Chat", MessageSquare)}
            {viewBtn("archived", "Archivio", Archive)}
            {viewBtn("trashed", "Cestino", Trash2)}
          </div>

          <AccountMenu user={user} />
        </div>
      </SheetContent>
    </Sheet>
  );
}
