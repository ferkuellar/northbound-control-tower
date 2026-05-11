"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { ScoreCards } from "@/components/scores/ScoreCards";
import { ScoreCharts } from "@/components/scores/ScoreCharts";
import { FindingsTable } from "@/components/findings/FindingsTable";
import { InventoryTable } from "@/components/resources/InventoryTable";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ApiError, getCloudAccounts, getCurrentUser, getFindings, getFindingsSummary, getResources, getScoreHistory, getScoresLatest, getScoresSummary } from "@/lib/api";
import { clearSession, getToken, setStoredUser } from "@/lib/auth";
import {
  countBy,
  countPublicResources,
  countUntaggedResources,
  labelize,
  openFindings,
  topRiskFindings,
} from "@/lib/formatters";
import type { DashboardData } from "@/lib/types";

type DashboardState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: DashboardData };

function numberCard(label: string, value: number | string, detail?: string) {
  return (
    <Card key={label}>
      <CardContent>
        <p className="text-sm font-medium text-steel">{label}</p>
        <p className="mt-2 text-3xl font-semibold text-ink">{value}</p>
        {detail ? <p className="mt-2 text-sm text-steel">{detail}</p> : null}
      </CardContent>
    </Card>
  );
}

function inlineStat(label: string, value: number | string) {
  return (
    <div key={label} className="rounded-md border border-slate-200 bg-slate-50 p-4">
      <p className="text-sm font-medium text-steel">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-ink">{value}</p>
    </div>
  );
}

function SummaryList({ title, items }: { title: string; items: Record<string, number> }) {
  const entries = Object.entries(items).sort((left, right) => right[1] - left[1]);
  return (
    <Card>
      <CardHeader>
        <h3 className="text-base font-semibold text-ink">{title}</h3>
      </CardHeader>
      <CardContent>
        {entries.length === 0 ? (
          <EmptyState title="No data available" />
        ) : (
          <div className="space-y-3">
            {entries.slice(0, 8).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between gap-4">
                <span className="text-sm text-steel">{labelize(key)}</span>
                <span className="rounded-md bg-slate-100 px-2 py-1 text-sm font-semibold text-ink">{value}</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function ExecutiveDashboard() {
  const router = useRouter();
  const [state, setState] = useState<DashboardState>({ status: "loading" });

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }

    async function loadDashboard(currentToken: string) {
      try {
        const [user, resources, findings, findingSummary, scoresLatest, scoreSummary, scoreHistory, cloudAccounts] =
          await Promise.all([
            getCurrentUser(currentToken),
            getResources(currentToken),
            getFindings(currentToken),
            getFindingsSummary(currentToken),
            getScoresLatest(currentToken),
            getScoresSummary(currentToken),
            getScoreHistory(currentToken),
            getCloudAccounts(currentToken),
          ]);

        setStoredUser(user);
        setState({
          status: "ready",
          data: { user, resources, findings, findingSummary, scoresLatest, scoreSummary, scoreHistory, cloudAccounts },
        });
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          clearSession();
          router.replace("/login");
          return;
        }
        setState({ status: "error", message: error instanceof Error ? error.message : "Dashboard unavailable" });
      }
    }

    void loadDashboard(token);
  }, [router]);

  if (state.status === "loading") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-surface px-4">
        <Card className="w-full max-w-md">
          <CardContent>
            <p className="text-sm font-semibold text-ink">Loading executive dashboard</p>
            <p className="mt-2 text-sm text-steel">Fetching scores, findings, and inventory from the backend.</p>
          </CardContent>
        </Card>
      </main>
    );
  }

  if (state.status === "error") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-surface px-4">
        <Card className="w-full max-w-lg">
          <CardContent>
            <p className="text-sm font-semibold text-risk">Dashboard unavailable</p>
            <p className="mt-2 text-sm text-steel">{state.message}</p>
          </CardContent>
        </Card>
      </main>
    );
  }

  const { data } = state;
  const activeFindings = openFindings(data.findings.items);
  const riskFindings = topRiskFindings(activeFindings);
  const providers = Object.keys(countBy(data.resources, (resource) => resource.provider));
  const resourcesByProvider = countBy(data.resources, (resource) => resource.provider);
  const resourcesByCategory = countBy(data.resources, (resource) => resource.resource_category);

  return (
    <DashboardShell user={data.user} cloudAccounts={data.cloudAccounts} onLogout={() => router.replace("/login")}>
      <div className="space-y-6">
        <section id="overview" className="space-y-4">
          <div>
            <h2 className="text-lg font-semibold text-ink">Overview</h2>
            <p className="text-sm text-steel">Executive scorecards from deterministic backend scores.</p>
          </div>
          <ScoreCards scores={data.scoresLatest.items} summary={data.scoreSummary} />
        </section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          {numberCard("Critical findings", data.findingSummary.by_severity.critical ?? 0)}
          {numberCard("High findings", data.findingSummary.by_severity.high ?? 0)}
          {numberCard("Open findings", activeFindings.length)}
          {numberCard("Cloud accounts", data.cloudAccounts.length)}
          {numberCard("Providers", providers.length || "N/A", providers.map((provider) => provider.toUpperCase()).join(", "))}
        </section>

        <section className="grid gap-4 xl:grid-cols-2">
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold text-ink">Inventory Summary</h2>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-3">
                {inlineStat("Total resources", data.resources.length)}
                {inlineStat("Public resources", countPublicResources(data.resources))}
                {inlineStat("Untagged resources", countUntaggedResources(data.resources))}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold text-ink">Risk Summary</h2>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {Object.entries(data.findingSummary.by_type).slice(0, 8).map(([type, count]) => (
                  <Badge key={type} tone={count > 0 ? "warning" : "neutral"}>
                    {labelize(type)}: {count}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </section>

        <section id="scores" className="space-y-4">
          <h2 className="text-lg font-semibold text-ink">Scores</h2>
          <ScoreCharts
            summary={data.scoreSummary}
            history={data.scoreHistory.items}
            findingsSummary={data.findingSummary}
          />
        </section>

        <section id="findings" className="space-y-4">
          <div className="grid gap-4 xl:grid-cols-4">
            <SummaryList title="Findings by Severity" items={data.findingSummary.by_severity} />
            <SummaryList title="Findings by Category" items={data.findingSummary.by_category} />
            <SummaryList title="Findings by Provider" items={data.findingSummary.by_provider} />
            <SummaryList title="Top Finding Types" items={data.findingSummary.by_type} />
          </div>
          <FindingsTable findings={data.findings.items} />
        </section>

        <section id="inventory">
          <InventoryTable resources={data.resources} />
        </section>

        <section id="risks" className="space-y-4">
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold text-ink">Risk Prioritization</h2>
              <p className="text-sm text-steel">Top deterministic findings ordered by severity and recency.</p>
            </CardHeader>
            <CardContent>
              {riskFindings.length === 0 ? (
                <EmptyState title="No active risk findings" description="Open or acknowledged findings will appear here." />
              ) : (
                <div className="space-y-3">
                  {riskFindings.map((finding) => (
                    <div key={finding.id} className="rounded-md border border-slate-200 p-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge tone={finding.severity === "critical" || finding.severity === "high" ? "danger" : "warning"}>
                          {labelize(finding.severity)}
                        </Badge>
                        <Badge>{labelize(finding.finding_type)}</Badge>
                        <Badge>{finding.provider.toUpperCase()}</Badge>
                      </div>
                      <p className="mt-3 font-medium text-ink">{finding.title}</p>
                      <p className="mt-1 text-sm text-steel">{finding.recommendation}</p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </section>

        <section id="trends" className="grid gap-4 xl:grid-cols-2">
          <SummaryList title="Resources by Provider" items={resourcesByProvider} />
          <SummaryList title="Resources by Category" items={resourcesByCategory} />
        </section>
      </div>
    </DashboardShell>
  );
}
