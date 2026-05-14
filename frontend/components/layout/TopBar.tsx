"use client";

import { ClipboardList, Gauge } from "lucide-react";

import { Button } from "@/components/ui/Button";

type TopBarProps = {
  cloudAccountsCount: number;
  providers: string[];
  tenantName?: string;
  selectedScope?: string;
  onRefresh?: () => void;
};

export function TopBar({ cloudAccountsCount, providers, tenantName, selectedScope, onRefresh }: TopBarProps) {
  const providerText = providers.length ? providers.join(", ") : "No providers";
  const context = `${cloudAccountsCount} cloud accounts across ${providerText} · Deterministic backend scores`;

  return (
    <header className="border-b border-northbound-border bg-northbound-bg px-4 py-3 md:px-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-lg font-semibold tracking-normal text-northbound-text">Executive Dashboard</h1>
            {tenantName ? (
              <span className="rounded-full border border-northbound-border bg-northbound-panel px-2 py-0.5 text-[11px] text-northbound-textMuted">
                {tenantName}
              </span>
            ) : null}
            {selectedScope ? (
              <span className="rounded-full border border-northbound-border bg-northbound-panel px-2 py-0.5 text-[11px] text-northbound-textMuted">
                {selectedScope}
              </span>
            ) : null}
          </div>
          <p className="mt-1 flex items-center gap-2 text-xs text-northbound-textMuted">
            <span className="h-1.5 w-1.5 rounded-full bg-[#1D9E75]" aria-hidden="true" />
            {context}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1 rounded-full border border-[#1D9E75]/35 bg-[#1D9E75]/15 px-3 py-1 text-xs font-semibold text-[#9FE1CB]">
            <span className="h-1.5 w-1.5 rounded-full bg-[#1D9E75]" aria-hidden="true" />
            Live
          </span>
          <Button variant="secondary" className="h-9 px-3" onClick={onRefresh}>
            <Gauge size={15} aria-hidden="true" />
            Refresh
          </Button>
          <Button variant="secondary" className="h-9 px-3">
            <ClipboardList size={15} aria-hidden="true" />
            Report
          </Button>
        </div>
      </div>
    </header>
  );
}
