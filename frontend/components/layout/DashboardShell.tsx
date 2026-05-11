"use client";

import {
  Activity,
  BarChart3,
  ClipboardList,
  Database,
  Gauge,
  LayoutDashboard,
  LogOut,
  ShieldAlert,
} from "lucide-react";
import type { ReactNode } from "react";

import { clearSession } from "@/lib/auth";
import type { CloudAccount, User } from "@/lib/types";
import { Button } from "@/components/ui/Button";

type DashboardShellProps = {
  user: User;
  cloudAccounts: CloudAccount[];
  children: ReactNode;
  onLogout: () => void;
};

const navItems = [
  { label: "Overview", href: "#overview", icon: LayoutDashboard },
  { label: "Inventory", href: "#inventory", icon: Database },
  { label: "Findings", href: "#findings", icon: ClipboardList },
  { label: "Scores", href: "#scores", icon: Gauge },
  { label: "Risks", href: "#risks", icon: ShieldAlert },
  { label: "Trends", href: "#trends", icon: BarChart3 },
];

export function DashboardShell({ user, cloudAccounts, children, onLogout }: DashboardShellProps) {
  const providers = Array.from(new Set(cloudAccounts.map((account) => account.provider.toUpperCase()))).join(", ");

  function handleLogout() {
    clearSession();
    onLogout();
  }

  return (
    <div className="min-h-screen bg-surface text-ink">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-72 border-r border-slate-200 bg-white lg:block">
        <div className="border-b border-slate-200 px-5 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-teal-50 text-signal">
              <Activity size={20} aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-semibold text-ink">Northbound</p>
              <p className="text-xs text-steel">Control Tower</p>
            </div>
          </div>
        </div>
        <nav className="space-y-1 px-3 py-4" aria-label="Dashboard navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <a
                key={item.href}
                href={item.href}
                className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-steel hover:bg-slate-100 hover:text-ink"
              >
                <Icon size={18} aria-hidden="true" />
                {item.label}
              </a>
            );
          })}
        </nav>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur">
          <div className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between lg:px-6">
            <div>
              <h1 className="text-xl font-semibold tracking-normal text-ink">Executive Dashboard</h1>
              <p className="text-sm text-steel">
                {cloudAccounts.length} cloud accounts {providers ? `across ${providers}` : "connected"}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
                <span className="text-steel">Signed in as </span>
                <span className="font-medium text-ink">{user.full_name}</span>
                <span className="ml-2 text-xs font-medium text-signal">{user.role}</span>
              </div>
              <Button variant="secondary" onClick={handleLogout}>
                <LogOut size={16} aria-hidden="true" />
                Logout
              </Button>
            </div>
          </div>
        </header>
        <main className="px-4 py-6 lg:px-6">{children}</main>
      </div>
    </div>
  );
}
