import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import { PackageCard } from "@/components/PackageCard";
import type { PackageCardData } from "@/lib/types";

export function PackageCarousel({ items }: { items: PackageCardData[] }) {
  return (
    <ScrollArea className="w-full">
      <div className="flex gap-4 pb-4">
        {items.map((p) => (
          <PackageCard key={p.id} data={p} />
        ))}
      </div>
      <ScrollBar orientation="horizontal" />
    </ScrollArea>
  );
}
