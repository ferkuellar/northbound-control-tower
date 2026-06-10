"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { FindingsTable } from "@/components/findings/FindingsTable";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { ApiError, getCurrentUser, getFindings } from "@/lib/api";
import { clearSession, getToken, setStoredUser } from "@/lib/auth";
import type { Finding, User } from "@/lib/types";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; user: User; findings: Finding[] };

export default function FindingsPage() {
  const router = useRouter();
  const [state, setState] = useState<State>({ status: "loading" });

  const load = useCallback(async () => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    try {
      const [user, response] = await Promise.all([
        getCurrentUser(token),
        getFindings(token),
      ]);
      setStoredUser(user);
      setState({ status: "ready", user, findings: response.items ?? [] });
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        clearSession();
        router.replace("/login");
        return;
      }
      setState({ status: "error", message: error instanceof Error ? error.message : "Findings unavailable" });
    }
  }, [router]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  if (state.status === "loading") return null;

  const user = state.status === "ready" ? state.user : null;
  const findings = state.status === "ready" ? state.findings : [];
  const openFindingsCount = findings.filter((f) => f.status === "open").length;

  return (
    <main className="min-h-screen bg-northbound-bg p-3 text-northbound-text">
      <div className="flex min-h-[calc(100vh-1.5rem)] flex-col overflow-hidden rounded-2xl border border-northbound-border md:flex-row">
        <Sidebar user={user} openFindingsCount={openFindingsCount} />
        <section className="flex min-w-0 flex-1 flex-col bg-northbound-bg">
          <TopBar tenantName="Findings" cloudAccountsCount={0} providers={[]} />
          <div className="flex-1 overflow-y-auto p-4">
            {state.status === "error" ? (
              <p className="text-sm text-red-200">{state.message}</p>
            ) : (
              <FindingsTable findings={findings} />
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
