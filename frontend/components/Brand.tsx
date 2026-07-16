import { cn } from "@/lib/utils";
import { Logo } from "@/components/Logo";

/**
 * The teal squircle badge holding the white plane mark — the same shape used for the
 * app icon / favicon. Reused across the sidebar, mobile header and the brand lockup.
 */
export function TravelMark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "grid size-10 shrink-0 place-items-center rounded-lg bg-primary text-primary-foreground shadow-sm",
        className,
      )}
    >
      <Logo className="size-6" />
    </span>
  );
}

/**
 * Horizontal logo lockup: the mark + the "Travel Agent" wordmark. Used where the brand
 * is presented on its own (e.g. the login screen).
 */
export function BrandLockup({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <TravelMark />
      <span className="text-2xl font-semibold tracking-tight">Travel Agent</span>
    </div>
  );
}
