"use client";

import {
  BarChart3,
  ClipboardList,
  Database,
  Gauge,
  LayoutDashboard,
  LogOut,
  ShieldAlert,
} from "lucide-react";
import Image from "next/image";
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
    <div className="min-h-screen bg-northbound-black100 text-northbound-white100">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-72 border-r border-northbound-black90 bg-northbound-black100 lg:block">
        <div className="border-b border-white/10 px-5 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-white/10 bg-northbound-black90 p-1.5">
              <Image src="/brand/logo-northbound.png" alt="Northbound logo" width={44} height={44} className="h-full w-full object-contain" priority />
            </div>
            <div>
              <p className="text-sm font-semibold text-northbound-white100">Northbound</p>
              <p className="text-xs text-northbound-white60">Control Tower</p>
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
                className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-northbound-white60 transition-colors first:bg-northbound-black90 first:text-northbound-white100 hover:bg-northbound-black90 hover:text-northbound-white100"
              >
                <Icon size={18} aria-hidden="true" />
                {item.label}
              </a>
            );
          })}
        </nav>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-10 border-b border-white/10 bg-northbound-black100">
          <div className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between lg:px-6">
            <div className="flex items-center gap-3">
              <Image src="/brand/logo-northbound.png" alt="Northbound logo" width={34} height={34} className="h-9 w-9 object-contain lg:hidden" />
              <div>
                <h1 className="text-xl font-semibold tracking-normal text-northbound-white100">Executive Dashboard</h1>
                <p className="text-sm text-northbound-white60">
                  {cloudAccounts.length} cloud accounts {providers ? `across ${providers}` : "connected"}
                </p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <div className="rounded-md border border-northbound-black80 bg-northbound-black90 px-3 py-2 text-sm">
                <span className="text-northbound-white60">Signed in as </span>
                <span className="font-medium text-northbound-white100">{user.full_name}</span>
                <span className="ml-2 text-xs font-medium text-emerald-300">{user.role}</span>
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
