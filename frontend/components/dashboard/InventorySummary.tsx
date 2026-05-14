import { Database } from "lucide-react";

import { SectionCard } from "@/components/dashboard/SectionCard";
import type { InventorySummary as InventorySummaryData } from "@/types/dashboard";

const tiles = [
  { key: "total_resources", label: "Total", className: "border-northbound-border bg-northbound-bg text-northbound-text" },
  { key: "public_resources", label: "Public", className: "border-[#A32D2D]/40 bg-[#A32D2D]/12 text-[#F7C1C1]" },
  { key: "untagged_resources", label: "Untagged", className: "border-[#BA7517]/40 bg-[#BA7517]/12 text-[#F6C177]" },
] as const;

export function InventorySummary({ inventory }: { inventory: InventorySummaryData }) {
  return (
    <SectionCard id="inventory" className="p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-northbound-text">
        <Database size={16} className="text-northbound-textMuted" aria-hidden="true" />
        Inventory Summary
      </div>
      <div className="grid grid-cols-3 gap-2">
        {tiles.map((tile) => (
          <div key={tile.key} className={`rounded-xl border px-3 py-3 text-center ${tile.className}`}>
            <p className="text-xl font-semibold">{inventory[tile.key]}</p>
            <p className="mt-1 text-[11px] opacity-80">{tile.label}</p>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}
