import type { ChatMsg } from "@/lib/useChat";
import type { PackageCardData } from "@/lib/types";

export function exportMarkdown(title: string, messages: ChatMsg[], packages: PackageCardData[]) {
  const lines = [`# ${title}`, ""];
  for (const m of messages) lines.push(`**${m.role === "user" ? "Tu" : "Agente"}:** ${m.content}`, "");
  if (packages.length) {
    lines.push("## Pacchetti", "");
    for (const p of packages) {
      lines.push(`- ${p.destination || "Pacchetto"} — ${Math.round(p.price_per_person)} ${p.currency} a persona`);
    }
  }
  const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${title || "viaggio"}.md`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
