"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { CommandHelpPanel } from "@/app/cloud-shell/components/CommandHelpPanel";
import { EvidencePanel } from "@/app/cloud-shell/components/EvidencePanel";
import { FindingContextPanel } from "@/app/cloud-shell/components/FindingContextPanel";
import { TerminalPanel } from "@/app/cloud-shell/components/TerminalPanel";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { ApiError, getCurrentUser } from "@/lib/api";
import { clearSession, getToken, setStoredUser } from "@/lib/auth";
import type { User } from "@/lib/types";

type State = { status: "loading" } | { status: "error"; message: string } | { status: "ready"; user: User; token: string };

export default function CloudShellPage() {
  const router = useRouter();
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    async function load() {
      const token = getToken();
      if (!token) {
        router.replace("/login");
        return;
      }
      try {
        const user = await getCurrentUser(token);
        setStoredUser(user);
        setState({ status: "ready", user, token });
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          clearSession();
          router.replace("/login");
          return;
        }
        setState({ status: "error", message: error instanceof Error ? error.message : "Cloud Shell unavailable" });
      }
    }
    void load();
  }, [router]);

  if (state.status === "loading") {
    return <main className="min-h-screen bg-northbound-bg" />;
  }

  if (state.status === "error") {
    return (
      <main className="min-h-screen bg-northbound-bg p-6 text-northbound-text">
        <div className="rounded-2xl border border-[#A32D2D]/50 bg-[#A32D2D]/10 p-6">
          <h1 className="font-semibold">Cloud Shell unavailable</h1>
          <p className="mt-2 text-sm text-northbound-textMuted">{state.message}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-northbound-bg p-3 text-northbound-text">
      <div className="flex min-h-[calc(100vh-1.5rem)] flex-col overflow-hidden rounded-2xl border border-northbound-border md:flex-row">
        <Sidebar user={state.user} />
        <section className="flex min-w-0 flex-1 flex-col bg-northbound-bg">
          <TopBar
            tenantName="Northbound Cloud Shell"
            selectedScope="Controlled provisioning console"
            cloudAccountsCount={0}
            providers={["AWS", "OCI"]}
          />
          <div className="grid flex-1 gap-4 overflow-y-auto p-4 xl:grid-cols-[minmax(0,1fr)_320px]">
            <TerminalPanel token={state.token} />
            <aside className="space-y-4">
              <CommandHelpPanel />
              <FindingContextPanel />
              <EvidencePanel />
            </aside>
          </div>
        </section>
      </div>
    </main>
  );
}
