import { ShieldAlert } from "lucide-react";

import { SectionCard } from "@/components/dashboard/SectionCard";
import type { RiskItem } from "@/types/dashboard";

export function getSeverityStyle(severity: RiskItem["severity"]): { dot: string; track: string; text: string } {
  if (severity === "critical") return { dot: "#A32D2D", track: "bg-[#A32D2D]/18", text: "text-[#F7C1C1]" };
  if (severity === "high") return { dot: "#BA7517", track: "bg-[#BA7517]/18", text: "text-[#F6C177]" };
  if (severity === "medium") return { dot: "#185FA5", track: "bg-[#185FA5]/18", text: "text-[#B5D4F4]" };
  return { dot: "#888780", track: "bg-northbound-border", text: "text-northbound-textMuted" };
}

export function RiskSummary({ risks }: { risks: RiskItem[] }) {
  const maxCount = Math.max(...risks.map((risk) => risk.count), 1);

  return (
    <SectionCard id="risks" className="p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-northbound-text">
        <ShieldAlert size={16} className="text-northbound-textMuted" aria-hidden="true" />
        Risk Summary
      </div>
      {risks.length === 0 ? (
        <div className="rounded-xl border border-dashed border-northbound-border bg-northbound-bg px-4 py-6 text-center text-sm text-northbound-textMuted">
          No active risks for the selected client.
        </div>
      ) : (
        <div className="space-y-3">
          {risks.map((risk) => {
            const style = getSeverityStyle(risk.severity);
            const width = Math.max(8, Math.round((risk.count / maxCount) * 100));
            return (
              <div key={risk.type} className="flex items-center gap-3">
                <div className="flex min-w-0 flex-1 items-center gap-2">
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: style.dot }} />
                  <span className="truncate text-xs text-northbound-textMuted">{risk.label}</span>
                </div>
                <div className="flex w-28 items-center gap-2">
                  <div className={`h-1.5 flex-1 overflow-hidden rounded-full ${style.track}`}>
                    <div className="h-1.5 rounded-full" style={{ width: `${width}%`, backgroundColor: style.dot }} />
                  </div>
                  <span className={`w-6 text-right text-xs font-semibold ${style.text}`}>{risk.count}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </SectionCard>
  );
}
