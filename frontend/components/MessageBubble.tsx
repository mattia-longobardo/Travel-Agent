import { Markdown } from "@/components/Markdown";
import { Logo } from "@/components/Logo";

export function formatStamp(iso?: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("it-IT", { dateStyle: "short", timeStyle: "short" });
}

export function MessageBubble({ role, content, createdAt }: { role: "user" | "assistant"; content: string; createdAt?: string }) {
  const isUser = role === "user";
  const stamp = formatStamp(createdAt);
  return (
    <div className={isUser ? "flex min-w-0 flex-col items-end" : "flex justify-start gap-3"}>
      {!isUser && (
        <span className="mt-1 hidden size-9 shrink-0 place-items-center rounded-lg bg-primary text-primary-foreground shadow-sm sm:grid">
          <Logo className="size-5" />
        </span>
      )}
      <div className={isUser ? "flex min-w-0 flex-col items-end" : "flex min-w-0 flex-col items-start"}>
        <div
          className={
            isUser
              ? "max-w-[min(42rem,88%)] rounded-lg bg-primary/10 px-4 py-3 text-sm leading-6 text-foreground ring-1 ring-primary/15 break-words"
              : "max-w-[min(46rem,92%)] rounded-lg bg-card px-4 py-3 text-sm leading-6 text-card-foreground shadow-sm ring-1 ring-border break-words"
          }
        >
          {isUser ? content : <Markdown>{content}</Markdown>}
        </div>
        {stamp && <time className="mt-1 px-1 text-[11px] text-muted-foreground">{stamp}</time>}
      </div>
    </div>
  );
}
