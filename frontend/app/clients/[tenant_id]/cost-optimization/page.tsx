"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { ReportActions } from "@/components/dashboard/ReportActions";
import { SectionCard } from "@/components/dashboard/SectionCard";
import { SectionLabel } from "@/components/dashboard/SectionLabel";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { Button } from "@/components/ui/Button";
import { costCsvUrl, getCostOptimization } from "@/lib/api/admin";
import { ApiError, getCurrentUser } from "@/lib/api";
import { downloadReportArtifact, generateReport, listReports, openReportPreview } from "@/lib/api/reports";
import { clearSession, getToken, setStoredUser } from "@/lib/auth";
import type { User } from "@/lib/types";
import type { CostOptimizationResponse } from "@/types/admin";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; user: User; data: CostOptimizationResponse };

function money(value: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(value);
}

export default function CostOptimizationPage() {
  const router = useRouter();
  const params = useParams<{ tenant_id: string }>();
  const tenantId = params.tenant_id;
  const [state, setState] = useState<State>({ status: "loading" });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    async function load() {
      const token = getToken();
      if (!token) {
        router.replace("/login");
        return;
      }
      try {
        const [user, data] = await Promise.all([getCurrentUser(token), getCostOptimization(token, tenantId)]);
        setStoredUser(user);
        setState({ status: "ready", user, data });
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          clearSession();
          router.replace("/login");
          return;
        }
        setState({ status: "error", message: error instanceof Error ? error.message : "Cost optimization unavailable" });
      }
    }
    void load();
  }, [router, tenantId]);

  async function downloadCsv() {
    const token = getToken();
    if (!token) return;
    const response = await fetch(costCsvUrl(tenantId), { headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) return;
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "clara-cost-optimization.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  async function generate(reportType: "executive" | "technical") {
    const token = getToken();
    if (!token) return;
    setBusy(true);
    try {
      const report = await generateReport(token, reportType, "pdf", tenantId);
      await downloadReportArtifact(token, report);
    } finally {
      setBusy(false);
    }
  }

  async function openLatest(mode: "preview" | "download" | "print") {
    const token = getToken();
    if (!token) return;
    const latest = (await listReports(token, tenantId))[0];
    if (!latest) return;
    if (mode === "download") {
      await downloadReportArtifact(token, latest);
      return;
    }
    await openReportPreview(token, latest, mode === "print");
  }

  if (state.status === "loading") return null;

  if (state.status === "error") {
    return (
      <main className="min-h-screen bg-northbound-bg p-6 text-northbound-text">
        <SectionCard className="mx-auto max-w-lg p-6">
          <h1 className="font-semibold">Cost optimization unavailable</h1>
          <p className="mt-2 text-sm text-northbound-textMuted">{state.message}</p>
        </SectionCard>
      </main>
    );
  }

  const { user, data } = state;
  const currency = data.case.currency;

  return (
    <main className="min-h-screen bg-northbound-bg p-3 text-northbound-text">
      <div className="flex min-h-[calc(100vh-1.5rem)] flex-col overflow-hidden rounded-2xl border border-northbound-border md:flex-row">
        <Sidebar user={user} />
        <section className="flex min-w-0 flex-1 flex-col bg-northbound-bg">
          <TopBar tenantName={data.tenant_name} selectedScope={`${data.case.provider.toUpperCase()} cost optimization`} cloudAccountsCount={1} providers={[data.case.provider.toUpperCase()]} />
          <div className="space-y-4 p-4">
            <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
              <SectionLabel eyebrow="FinOps Case Study" title="Clara AWS Cost Optimization" description={data.case.description} />
              <div className="flex flex-wrap gap-2">
                <Button onClick={() => void downloadCsv()}>Download Cost Model CSV</Button>
                <ReportActions
                  isBusy={busy}
                  onGenerateExecutive={() => void generate("executive")}
                  onGenerateTechnical={() => void generate("technical")}
                  onPreviewLatest={() => void openLatest("preview")}
                  onDownloadLatest={() => void openLatest("download")}
                  onPrint={() => void openLatest("print")}
                />
              </div>
            </div>

            <section className="grid gap-3 md:grid-cols-3">
              <SectionCard className="p-4">
                <p className="text-xs text-northbound-textMuted">Current monthly spend</p>
                <p className="mt-2 text-3xl font-semibold">{money(data.case.monthly_spend, currency)}</p>
              </SectionCard>
              <SectionCard className="p-4">
                <p className="text-xs text-northbound-textMuted">Estimated monthly savings</p>
                <p className="mt-2 text-3xl font-semibold text-[#9FE1CB]">{money(data.estimated_monthly_savings, currency)}</p>
              </SectionCard>
              <SectionCard className="p-4">
                <p className="text-xs text-northbound-textMuted">Estimated annual savings</p>
                <p className="mt-2 text-3xl font-semibold text-[#9FE1CB]">{money(data.estimated_annual_savings, currency)}</p>
              </SectionCard>
            </section>

            <section className="grid gap-4 xl:grid-cols-2">
              <SectionCard className="p-4">
                <SectionLabel title="Current Cost Breakdown" />
                <div className="mt-4 space-y-3">
                  {data.case.service_breakdown.map((service) => (
                    <div key={service.id}>
                      <div className="flex justify-between text-sm">
                        <span>{service.service_name}</span>
                        <span className="text-northbound-textMuted">{money(service.monthly_cost, currency)} · {service.percentage}%</span>
                      </div>
                      <div className="mt-1 h-2 rounded-full bg-northbound-border">
                        <div className="h-2 rounded-full bg-[#1D9E75]" style={{ width: `${service.percentage}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </SectionCard>
              <SectionCard className="p-4">
                <SectionLabel title="Architecture Diagram" description="High-level current and proposed state. Export diagram planned." />
                <div className="mt-4 grid gap-3">
                  <div className="rounded-xl border border-northbound-border bg-northbound-bg p-3">
                    <p className="text-xs font-semibold text-northbound-textMuted">Current</p>
                    <p className="mt-2 text-sm">{data.architecture_current.join(" -> ")}</p>
                  </div>
                  <div className="rounded-xl border border-[#1D9E75]/40 bg-[#1D9E75]/10 p-3">
                    <p className="text-xs font-semibold text-[#9FE1CB]">Proposed</p>
                    <p className="mt-2 text-sm text-northbound-textSecondary">{data.architecture_proposed.join(" + ")}</p>
                  </div>
                </div>
              </SectionCard>
            </section>

            <SectionCard className="p-4">
              <SectionLabel title="Prioritized Recommendations" description="Savings are estimates based on explicit test case assumptions, not exact AWS pricing." />
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full divide-y divide-northbound-border text-sm">
                  <thead className="text-left text-xs uppercase text-northbound-textMuted">
                    <tr>
                      <th className="px-3 py-2">Priority</th>
                      <th className="px-3 py-2">Action</th>
                      <th className="px-3 py-2">Service</th>
                      <th className="px-3 py-2">Savings</th>
                      <th className="px-3 py-2">Effort</th>
                      <th className="px-3 py-2">Assumptions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/10">
                    {data.case.recommendations.map((item) => (
                      <tr key={item.id}>
                        <td className="px-3 py-3">{item.priority}</td>
                        <td className="px-3 py-3">
                          <p className="font-semibold text-northbound-text">{item.title}</p>
                          <p className="text-xs text-northbound-textMuted">{item.description}</p>
                        </td>
                        <td className="px-3 py-3">{item.service_name}</td>
                        <td className="px-3 py-3 text-[#9FE1CB]">{money(item.estimated_monthly_savings, currency)}/mo</td>
                        <td className="px-3 py-3">{item.implementation_effort}</td>
                        <td className="max-w-sm px-3 py-3 text-xs text-northbound-textMuted">{item.assumptions}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </SectionCard>

            <SectionCard className="p-4">
              <SectionLabel title="Implementation Plan" />
              <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-northbound-textSecondary">
                {data.implementation_plan.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            </SectionCard>
          </div>
        </section>
      </div>
    </main>
  );
}
