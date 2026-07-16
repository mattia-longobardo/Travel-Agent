"use client";
import { useState, useCallback, useRef } from "react";
import { streamChat } from "@/lib/sse";
import { getCoords } from "@/lib/geo";
import type {
  AccommodationType,
  AgentStep,
  BriefData,
  ChatTitleEvent,
  PackageCardData,
  QuestionEvent,
  ResultBatch,
  SearchMode,
} from "@/lib/types";

export interface ChatMsg { role: "user" | "assistant"; content: string; created_at?: string; }

export interface HydrateInput {
  messages: ChatMsg[];
  resultBatches: ResultBatch[];
  brief: BriefData | null;
  question?: QuestionEvent | null;
}

export function useChat(chatId: number) {
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [resultBatches, setResultBatches] = useState<ResultBatch[]>([]);
  const [selectedResultBatchId, setSelectedResultBatchId] = useState<string | null>(null);
  const [question, setQuestion] = useState<QuestionEvent | null>(null);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [brief, setBrief] = useState<BriefData | null>(null);
  const [chatTitle, setChatTitle] = useState<ChatTitleEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  // The chat id of the CURRENT in-flight run. A lazily-created chat streams under a
  // chatIdOverride while the hook still renders with the old id, so `cancel` must stop
  // the run's actual chat, not the hook's stale prop.
  const activeChatRef = useRef<number | null>(null);
  const batchSequenceRef = useRef(0);

  const selectedResultBatch =
    resultBatches.find((batch) => batch.id === selectedResultBatchId) ?? resultBatches.at(-1) ?? null;
  const packages = selectedResultBatch?.packages ?? [];

  const reset = useCallback(() => {
    setSteps([]); setResultBatches([]); setSelectedResultBatchId(null); setQuestion(null);
    setMessages([]); setBrief(null); setChatTitle(null); setError(null); setSending(false);
  }, []);

  const hydrate = useCallback((data: HydrateInput) => {
    setMessages(data.messages);
    setResultBatches(data.resultBatches);
    setSelectedResultBatchId(data.resultBatches.at(-1)?.id ?? null);
    setBrief(data.brief);
    setSteps([]); setQuestion(data.question ?? null); setChatTitle(null); setError(null); setSending(false);
  }, []);

  // `chatIdOverride` lets the caller target a chat created in the same tick (lazy "new trip"),
  // before the hook re-renders with the new id.
  const send = useCallback(async (
    text: string,
    answerTo?: string,
    chatIdOverride?: number,
    opts?: {
      generateMore?: boolean;
      refineText?: string;
      searchMode?: SearchMode;
      accommodationType?: AccommodationType;
      onChatTitle?: (event: ChatTitleEvent) => void;
    },
  ) => {
    const target = chatIdOverride ?? chatId;
    activeChatRef.current = target;
    setSending(true); setSteps([]); setQuestion(null); setChatTitle(null); setError(null);
    setMessages((m) => [...m, { role: "user", content: text, created_at: new Date().toISOString() }]);
    const coords = await getCoords();
    const controller = new AbortController();
    abortRef.current = controller;
    const batchId = `run-${target}-${Date.now()}-${++batchSequenceRef.current}`;
    const batchCreatedAt = new Date().toISOString();
    let batchPackages: PackageCardData[] = [];
    let batchCompleted = false;
    let batchFailed = false;

    const discardLiveBatch = () => {
      if (batchPackages.length === 0) return;
      setResultBatches((batches) => batches.filter((batch) => batch.id !== batchId));
    };

    try {
      await streamChat(`/api/chats/${target}/messages`, {
        content: text,
        coords,
        answer_to: answerTo,
        generate_more: opts?.generateMore ?? false,
        refine_text: opts?.refineText ?? "",
        search_mode: opts?.searchMode,
        accommodation_type: opts?.accommodationType,
      },
        (ev) => {
          if (ev.type === "agent_step") setSteps((s) => [...s, ev]);
          else if (ev.type === "package") {
            batchPackages = [...batchPackages, ev.data];
            const nextBatch: ResultBatch = {
              id: batchId,
              packages: batchPackages,
              created_at: batchCreatedAt,
            };
            setResultBatches((batches) => {
              const index = batches.findIndex((batch) => batch.id === batchId);
              if (index < 0) return [...batches, nextBatch];
              return batches.map((batch, i) => (i === index ? nextBatch : batch));
            });
            setSelectedResultBatchId(batchId);
          }
          else if (ev.type === "question") setQuestion(ev);
          else if (ev.type === "brief") setBrief(ev.data);
          else if (ev.type === "message") setMessages((m) => [...m, { role: "assistant", content: ev.content, created_at: new Date().toISOString() }]);
          else if (ev.type === "stopped") {
            batchFailed = true;
            discardLiveBatch();
            setMessages((m) => [...m, { role: "assistant", content: "🛑 Ricerca interrotta. Scrivimi pure per riprovare o modificare la richiesta.", created_at: new Date().toISOString() }]);
          }
          else if (ev.type === "chat_title") {
            setChatTitle(ev);
            opts?.onChatTitle?.(ev);
          }
          else if (ev.type === "error") {
            batchFailed = true;
            discardLiveBatch();
            setError(ev.message);
          }
          else if (ev.type === "done") batchCompleted = true;
        },
        controller.signal);
    } finally {
      if (!batchCompleted || batchFailed) discardLiveBatch();
      abortRef.current = null;
      setSending(false);
    }
  }, [chatId]);

  // Stop the in-flight run. The backend cancels the run and emits a `stopped` event
  // followed by `done`, which closes the stream cleanly — the `stopped` handler in `send`
  // renders the interrotto bubble and `send`'s finally clears `sending`. We only abort as a
  // fallback (capturing THIS run's controller) in case the stream never closes.
  const cancel = useCallback(async () => {
    const controller = abortRef.current;
    const target = activeChatRef.current ?? chatId;
    try {
      await fetch(`/api/chats/${target}/stop`, { method: "POST", credentials: "include" });
    } catch {
      /* best-effort */
    }
    setTimeout(() => controller?.abort(), 2000);
  }, [chatId]);

  // `setSending` is exposed so a reloaded page can show the working state while it polls a
  // still-running server-side search back into view (see the resume logic in page.tsx).
  return {
    steps,
    packages,
    resultBatches,
    selectedResultBatchId: selectedResultBatch?.id ?? null,
    selectResultBatch: setSelectedResultBatchId,
    question,
    messages,
    brief,
    chatTitle,
    error,
    sending,
    send,
    cancel,
    hydrate,
    reset,
    setSending,
  };
}
