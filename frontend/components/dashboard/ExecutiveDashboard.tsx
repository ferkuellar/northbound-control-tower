"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ErrorState } from "@/components/dashboard/ErrorState";
import { FindingsSummaryBar } from "@/components/dashboard/FindingsSummaryBar";
import { InventorySummary } from "@/components/dashboard/InventorySummary";
import { ReportActions } from "@/components/dashboard/ReportActions";
import { RiskSummary } from "@/components/dashboard/RiskSummary";
import { ScoreGrid } from "@/components/dashboard/ScoreGrid";
import { SectionLabel } from "@/components/dashboard/SectionLabel";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { getExecutiveDashboard } from "@/lib/api/dashboard";
import { listAdminTenants } from "@/lib/api/admin";
import { downloadReportArtifact, generateReport, listReports, openReportPreview } from "@/lib/api/reports";
import { clearSession, getToken, setStoredUser } from "@/lib/auth";
import { ApiError, getCurrentUser } from "@/lib/api";
import type { User } from "@/lib/types";
import type { AdminTenant } from "@/types/admin";
import type { ExecutiveDashboardData } from "@/types/dashboard";

type DashboardState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; user: User; tenants: AdminTenant[]; data: ExecutiveDashboardData };

function formatRelativeTime(value: string): string {
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return "Unknown";
  const minutes = Math.max(0, Math.round((Date.now() - timestamp) / 60000));
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  return `${Math.round(hours / 24)} days ago`;
}

export function ExecutiveDashboard() {
  const router = useRouter();
  const [selectedTenantId, setSelectedTenantId] = useState<string>("");
  const [selectedCloudAccountId, setSelectedCloudAccountId] = useState<string>("");
  const [state, setState] = useState<DashboardState>({ status: "loading" });
  const [reportBusy, setReportBusy] = useState(false);

  const loadDashboard = useCallback(
    async (tenantId?: string) => {
      const token = getToken();
      if (!token) {
        router.replace("/login");
        return;
      }
      setState((current) => (current.status === "ready" ? current : { status: "loading" }));
      try {
        const user = await getCurrentUser(token);
        const tenants = user.role === "ADMIN" ? await listAdminTenants(token).catch(() => []) : [];
        const effectiveTenantId = tenantId || selectedTenantId || tenants[0]?.id;
        const data = await getExecutiveDashboard(token, effectiveTenantId);
        setStoredUser(user);
        setSelectedTenantId(effectiveTenantId || data.tenant?.id || user.tenant_id);
        setSelectedCloudAccountId((current) => current || data.cloud_accounts?.[0]?.id || "");
        setState({ status: "ready", user, tenants, data });
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          clearSession();
          router.replace("/login");
          return;
        }
        setState({ status: "error", message: error instanceof Error ? error.message : "Dashboard unavailable" });
      }
    },
    [router, selectedTenantId],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadDashboard();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadDashboard]);

  const selectedTenant = useMemo(() => {
    if (state.status !== "ready") return null;
    return state.tenants.find((tenant) => tenant.id === selectedTenantId) ?? null;
  }, [selectedTenantId, state]);

  async function generate(reportType: "executive" | "technical") {
    const token = getToken();
    if (!token) return;
    setReportBusy(true);
    try {
      const report = await generateReport(token, reportType, "pdf", selectedTenantId);
      await downloadReportArtifact(token, report);
    } finally {
      setReportBusy(false);
    }
  }

  async function openLatest(mode: "preview" | "download" | "print") {
    const token = getToken();
    if (!token) return;
    const reports = await listReports(token, selectedTenantId);
    const latest = reports[0];
    if (!latest) return;
    if (mode === "download") {
      await downloadReportArtifact(token, latest);
      return;
    }
    await openReportPreview(token, latest, mode === "print");
  }

  if (state.status === "loading") {
    return null;
  }

  if (state.status === "error") {
    return <ErrorState message={state.message} onRetry={() => void loadDashboard(selectedTenantId)} />;
  }

  const { data, user, tenants } = state;
  const selectedCloudAccount = data.cloud_accounts?.find((account) => account.id === selectedCloudAccountId) ?? data.cloud_accounts?.[0];
  const tenantName = selectedTenant?.name ?? data.tenant?.name ?? "Current tenant";

  return (
    <main className="min-h-screen bg-northbound-bg p-3 text-northbound-text">
      <div className="flex min-h-[calc(100vh-1.5rem)] flex-col overflow-hidden rounded-2xl border border-northbound-border md:flex-row">
        <Sidebar user={user} openFindingsCount={data.findings.open} />
        <section className="flex min-w-0 flex-1 flex-col bg-northbound-bg">
          <TopBar
            tenantName={tenantName}
            selectedScope={selectedCloudAccount ? `${selectedCloudAccount.name} · ${selectedCloudAccount.provider.toUpperCase()}` : "Select cloud account"}
            cloudAccountsCount={data.findings.cloud_accounts}
            providers={data.findings.providers}
            onRefresh={() => void loadDashboard(selectedTenantId)}
          />
          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            <section className="grid gap-3 lg:grid-cols-[1fr_auto] lg:items-end">
              <div className="grid gap-3 md:grid-cols-2">
                <label className="space-y-1">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-northbound-textMuted">Client</span>
                  <Select value={selectedTenantId} onChange={(event) => void loadDashboard(event.target.value)}>
                    <option value="">{tenants.length ? "Select client" : tenantName}</option>
                    {tenants.map((tenant) => (
                      <option key={tenant.id} value={tenant.id}>
                        {tenant.name}
                      </option>
                    ))}
                  </Select>
                </label>
                <label className="space-y-1">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-northbound-textMuted">Cloud account</span>
                  <Select value={selectedCloudAccountId} onChange={(event) => setSelectedCloudAccountId(event.target.value)}>
                    {data.cloud_accounts?.length ? null : <option value="">Select cloud account</option>}
                    {data.cloud_accounts?.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.name} · {account.provider.toUpperCase()}
                      </option>
                    ))}
                  </Select>
                </label>
              </div>
              <div className="rounded-xl border border-northbound-border bg-northbound-panel px-4 py-3 text-xs text-northbound-textMuted">
                <span className="font-semibold text-northbound-textSecondary">Last scan:</span> {formatRelativeTime(data.last_collected_at)}
              </div>
            </section>

            <section id="overview" className="space-y-3">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                <SectionLabel eyebrow="Operational Scores" title={`${tenantName} cloud operations`} description="Compact V2 score overview from deterministic backend data." />
                <ReportActions
                  isBusy={reportBusy}
                  onGenerateExecutive={() => void generate("executive")}
                  onGenerateTechnical={() => void generate("technical")}
                  onPreviewLatest={() => void openLatest("preview")}
                  onDownloadLatest={() => void openLatest("download")}
                  onPrint={() => void openLatest("print")}
                />
              </div>
              <ScoreGrid data={data} />
            </section>

            <FindingsSummaryBar findings={data.findings} />

            <section className="grid gap-3 xl:grid-cols-2">
              <InventorySummary inventory={data.inventory} />
              <RiskSummary risks={data.risks} />
            </section>

            <section id="cloud-accounts" className="rounded-2xl border border-northbound-border bg-northbound-panel p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <SectionLabel title="Client cloud context" description="The selected client controls inventory, findings, scores, reports, and analysis scope." />
                <Button variant="secondary" onClick={() => router.push("/admin/clients")}>Manage Clients</Button>
              </div>
            </section>
          </div>
        </section>
      </div>
    </main>
  );
}
