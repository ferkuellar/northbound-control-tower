import { Database, Gauge, ShieldAlert } from "lucide-react";

import type { FindingsSummary } from "@/types/dashboard";

type Tile = {
  label: string;
  value: string | number;
  icon: typeof ShieldAlert;
  className: string;
  helper?: string;
};

export function FindingsSummaryBar({ findings }: { findings: FindingsSummary }) {
  const tiles: Tile[] = [
    {
      label: "Critical",
      value: findings.critical,
      icon: ShieldAlert,
      className: "border-[#A32D2D]/45 bg-[#A32D2D]/12 text-[#F7C1C1]",
    },
    {
      label: "High",
      value: findings.high,
      icon: ShieldAlert,
      className: "border-[#BA7517]/45 bg-[#BA7517]/12 text-[#F6C177]",
    },
    {
      label: "Open",
      value: findings.open,
      icon: ShieldAlert,
      className: "border-northbound-border bg-northbound-panel text-northbound-text",
    },
    {
      label: "Accounts",
      value: findings.cloud_accounts,
      icon: Database,
      className: "border-northbound-border bg-northbound-panel text-northbound-text",
    },
    {
      label: "Providers",
      value: findings.providers.length || "N/A",
      icon: Gauge,
      helper: findings.providers.join(", "),
      className: "border-[#185FA5]/45 bg-[#185FA5]/14 text-[#B5D4F4]",
    },
  ];

  return (
    <div id="findings" className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
      {tiles.map((tile) => {
        const Icon = tile.icon;
        return (
          <section key={tile.label} className={`rounded-xl border px-3 py-3 ${tile.className}`}>
            <div className="flex items-center justify-between gap-2">
              <p className="text-[11px] font-medium opacity-85">{tile.label}</p>
              <Icon size={14} aria-hidden="true" />
            </div>
            <p className="mt-1 text-2xl font-semibold leading-none">{tile.value}</p>
            {tile.helper ? <p className="mt-1 truncate text-[10px] opacity-75">{tile.helper}</p> : null}
          </section>
        );
      })}
    </div>
  );
}
