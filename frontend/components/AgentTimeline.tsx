"use client";
import { motion } from "framer-motion";
import {
  Brain,
  Check,
  CircleAlert,
  Clock3,
  Hotel,
  Map as MapIcon,
  PackageCheck,
  Plane,
  Sparkles,
  WalletCards,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { AgentName, AgentStep } from "@/lib/types";

const AGENT_ICON: Record<AgentName, typeof Brain> = {
  intake: Brain,
  scout: MapIcon,
  flight: Plane,
  hotel: Hotel,
  package: PackageCheck,
  optimizer: WalletCards,
  presenter: Sparkles,
};

export function AgentTimeline({ steps }: { steps: AgentStep[] }) {
  const latest = new Map<string, AgentStep>();
  steps.forEach((s) => latest.set(s.agent, s));

  return (
    <div className="flex flex-col gap-2">
      {[...latest.values()].map((s) => (
        <motion.div
          key={s.agent}
          data-testid={`step-${s.agent}`}
          data-status={s.status}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          className="grid grid-cols-[2rem_minmax(0,1fr)_auto] items-center gap-3 rounded-lg border bg-background px-3 py-2 text-sm"
        >
          <span
            className={cn(
              "grid size-8 place-items-center rounded-lg",
              s.status === "done" && "bg-primary/10 text-primary",
              s.status === "running" && "bg-[var(--travel-coral-soft)] text-[var(--travel-coral)]",
              s.status === "error" && "bg-destructive/10 text-destructive"
            )}
          >
            {(() => {
              const Icon = AGENT_ICON[s.agent] || Brain;
              return <Icon aria-hidden="true" />;
            })()}
          </span>
          <span className="min-w-0">
            <span className="block truncate font-medium text-foreground">{s.label}</span>
            <span className="block text-xs text-muted-foreground">{s.agent}</span>
          </span>
          <span
            className={cn(
              "grid size-7 place-items-center rounded-md",
              s.status === "done" && "bg-primary text-primary-foreground",
              s.status === "running" && "bg-secondary text-secondary-foreground",
              s.status === "error" && "bg-destructive/10 text-destructive"
            )}
          >
            {s.status === "done" && <Check aria-hidden="true" />}
            {s.status === "running" && <Clock3 aria-hidden="true" />}
            {s.status === "error" && <CircleAlert aria-hidden="true" />}
          </span>
        </motion.div>
      ))}
    </div>
  );
}
