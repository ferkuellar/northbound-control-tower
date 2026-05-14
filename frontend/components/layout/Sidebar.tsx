"use client";

import {
  BarChart3,
  ClipboardList,
  Database,
  Gauge,
  LayoutDashboard,
  ShieldAlert,
} from "lucide-react";
import Image from "next/image";

import type { User } from "@/lib/types";

type SidebarProps = {
  user: User | null;
  openFindingsCount?: number;
};

type NavItem = {
  label: string;
  href: string;
  icon: typeof LayoutDashboard;
  active?: boolean;
  badge?: boolean;
};

const operations: NavItem[] = [
  { label: "Overview", href: "/dashboard", icon: LayoutDashboard, active: true },
  { label: "Inventory", href: "#inventory", icon: Database },
  { label: "Findings", href: "#findings", icon: ClipboardList, badge: true },
  { label: "Scores", href: "#scores", icon: BarChart3 },
  { label: "Risks", href: "#risks", icon: ShieldAlert },
  { label: "Trends", href: "#trends", icon: Gauge },
];

const administration: NavItem[] = [
  { label: "Clients", href: "/admin/clients", icon: LayoutDashboard },
  { label: "Cloud Accounts", href: "#cloud-accounts", icon: Database },
  { label: "Reports", href: "#reports", icon: ClipboardList },
  { label: "Audit Logs", href: "#audit-logs", icon: ClipboardList },
  { label: "Settings", href: "#settings", icon: Gauge },
];

function NavGroup({
  title,
  items,
  openFindingsCount,
}: {
  title: string;
  items: NavItem[];
  openFindingsCount?: number;
}) {
  return (
    <div className="space-y-1">
      <p className="px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-northbound-muted">{title}</p>
      <div className="space-y-1">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <a
              key={item.href}
              href={item.href}
              className={`flex min-h-9 items-center gap-2 border-l-2 px-3 py-2 text-xs outline-none transition focus-visible:ring-2 focus-visible:ring-northbound-white80 ${
                item.active
                  ? "border-[#1D9E75] bg-northbound-panel text-northbound-text"
                  : "border-transparent text-northbound-textMuted hover:bg-northbound-panel hover:text-northbound-textSecondary"
              }`}
            >
              <Icon size={15} aria-hidden="true" />
              <span className="truncate">{item.label}</span>
              {item.badge && openFindingsCount ? (
                <span className="ml-auto rounded-full border border-[#BA7517]/40 bg-[#BA7517]/20 px-1.5 py-0.5 text-[10px] font-semibold text-[#F6C177]">
                  {openFindingsCount}
                </span>
              ) : null}
            </a>
          );
        })}
      </div>
    </div>
  );
}

export function Sidebar({ user, openFindingsCount }: SidebarProps) {
  return (
    <aside className="flex w-full shrink-0 flex-col border-b border-northbound-border bg-northbound-bg md:min-h-screen md:w-60 md:border-b-0 md:border-r">
      <div className="border-b border-northbound-border px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-northbound-border bg-northbound-panel p-1.5">
            <Image src="/brand/logo-northbound.png" alt="Northbound logo" width={36} height={36} className="h-full w-full object-contain" priority />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-northbound-text">Northbound</p>
            <p className="truncate text-[11px] tracking-wide text-northbound-textMuted">Control Tower</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-5 px-0 py-4" aria-label="Dashboard navigation">
        <NavGroup title="Operations" items={operations} openFindingsCount={openFindingsCount} />
        <NavGroup title="Administration" items={administration} />
      </nav>

      <div className="border-t border-northbound-border px-4 py-4">
        <div className="flex items-center gap-3 rounded-xl border border-northbound-border bg-northbound-panel p-2.5">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#0F6E56] text-xs font-semibold text-[#9FE1CB]">
            {(user?.full_name ?? "N").slice(0, 1).toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-semibold text-northbound-text">{user?.full_name ?? "Northbound"}</p>
            <p className="truncate text-[10px] font-medium text-northbound-textMuted">{user?.role ?? "VIEWER"}</p>
          </div>
          <Gauge size={14} className="text-northbound-textMuted" aria-hidden="true" />
        </div>
      </div>

      <div className="hidden items-center gap-2 border-t border-northbound-border px-4 py-3 text-[10px] text-northbound-muted md:flex">
        <Gauge size={13} aria-hidden="true" />
        Compact V2 control view
      </div>
    </aside>
  );
}
