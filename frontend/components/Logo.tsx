import { cn } from "@/lib/utils";

/**
 * Travel Agent brand mark: an origami paper plane tracing a short dotted route to a
 * destination dot. Two facets (the lighter far wing + full near wing) give the folded-
 * paper read. Drawn with `currentColor` so it inherits the surrounding badge colour.
 */
export function Logo({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      role="img"
      aria-label="Travel Agent"
      className={cn("size-6", className)}
    >
      {/* destination dot */}
      <circle cx="21" cy="3.4" r="1.5" fill="currentColor" />
      {/* dotted travel route from the plane's nose to the dot */}
      <path
        d="M18.6 5.6 Q20.2 4.2 20.6 3.7"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.1"
        strokeLinecap="round"
        strokeDasharray="0.1 1.5"
        opacity="0.6"
      />
      {/* far/top wing (lighter — the fold) */}
      <path d="M18.7 5.7 2.6 7.1 9.6 12.4Z" fill="currentColor" opacity="0.78" />
      {/* near/bottom wing */}
      <path d="M18.7 5.7 9.6 12.4 8.2 18.5Z" fill="currentColor" />
    </svg>
  );
}
