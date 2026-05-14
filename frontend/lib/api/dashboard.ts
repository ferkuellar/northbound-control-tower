import {
  apiFetch,
  ApiError,
  getCloudAccounts,
  getFindings,
  getFindingsSummary,
  getResources,
  getScoresLatest,
  getScoresSummary,
} from "@/lib/api";
import { countPublicResources, countUntaggedResources, labelize } from "@/lib/formatters";
import type { CloudAccount, CloudScore, Finding, Resource, ScoreSummary } from "@/lib/types";
import type {
  DimensionScore,
  ExecutiveDashboardData,
  RiskItem,
  ScoreLabel,
  ScoreTrend,
} from "@/types/dashboard";

const SCORE_ORDER = [
  ["finops", "FinOps"],
  ["governance", "Governance"],
  ["observability", "Observability"],
  ["security_baseline", "Security"],
  ["resilience", "Resilience"],
] as const;

const SEVERITY_RANK: Record<RiskItem["severity"], number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
};

function toScoreLabel(score: number): ScoreLabel {
  if (score >= 90) return "Excellent";
  if (score >= 75) return "Good";
  if (score >= 60) return "Fair";
  if (score >= 40) return "Poor";
  return "Critical";
}

function normalizeTrend(value: string | null | undefined): ScoreTrend {
  if (value === "improving" || value === "stable" || value === "declining" || value === "degrading") {
    return value;
  }
  return "unknown";
}

function findScore(scores: CloudScore[], key: string): CloudScore | undefined {
  return scores.find((score) => score.score_type === key);
}

function scoreValue(score: CloudScore | undefined, summary: ScoreSummary, key: string): number {
  const value = score?.score_value ?? (key === "overall" ? summary.overall_score : summary.domain_scores[key]);
  return typeof value === "number" ? Math.max(0, Math.min(100, Math.round(value))) : 100;
}

function topDriver(score: CloudScore | undefined, summary: ScoreSummary, key: string): string | null {
  if (score?.summary) return score.summary;
  const driver = summary.top_drivers.find((item) => item.score_type === key || item.type === key);
  if (!driver) return null;
  const label = driver.finding_type ?? driver.type ?? driver.title;
  return typeof label === "string" ? labelize(label) : null;
}

function buildDimensionScore(
  key: string,
  label: string,
  scores: CloudScore[],
  summary: ScoreSummary,
): DimensionScore {
  const score = findScore(scores, key);
  const value = scoreValue(score, summary, key);
  const grade = typeof score?.grade === "string" ? labelize(score.grade) : toScoreLabel(value);
  return {
    key,
    label,
    score: value,
    label_text: grade as ScoreLabel,
    trend: normalizeTrend(score?.trend ?? summary.trends[key]),
    top_driver: topDriver(score, summary, key),
  };
}

function latestTimestamp(resources: Resource[], scores: CloudScore[]): string {
  const timestamps = [
    ...resources.map((resource) => resource.discovered_at),
    ...scores.map((score) => score.calculated_at),
  ]
    .map((value) => new Date(value).getTime())
    .filter((value) => Number.isFinite(value));
  const latest = timestamps.length ? Math.max(...timestamps) : Date.now();
  return new Date(latest).toISOString();
}

function activeFindings(findings: Finding[]): Finding[] {
  return findings.filter((finding) => finding.status === "open" || finding.status === "acknowledged");
}

function riskSeverity(current: RiskItem["severity"], next: Finding["severity"]): RiskItem["severity"] {
  const normalized = next === "informational" ? "low" : next;
  return SEVERITY_RANK[normalized] > SEVERITY_RANK[current] ? normalized : current;
}

function buildRisks(findings: Finding[]): RiskItem[] {
  const risks = new Map<string, RiskItem>();

  activeFindings(findings).forEach((finding) => {
    const existing = risks.get(finding.finding_type);
    if (!existing) {
      risks.set(finding.finding_type, {
        type: finding.finding_type,
        label: labelize(finding.finding_type),
        count: 1,
        severity: finding.severity === "informational" ? "low" : finding.severity,
      });
      return;
    }
    existing.count += 1;
    existing.severity = riskSeverity(existing.severity, finding.severity);
  });

  return Array.from(risks.values())
    .sort((left, right) => SEVERITY_RANK[right.severity] - SEVERITY_RANK[left.severity] || right.count - left.count)
    .slice(0, 6);
}

function uniqueProviders(accounts: CloudAccount[], resources: Resource[]): string[] {
  const providers = [...accounts.map((account) => account.provider), ...resources.map((resource) => resource.provider)];
  return Array.from(new Set(providers.filter(Boolean).map((provider) => provider.toUpperCase()))).sort();
}

async function aggregateExecutiveDashboard(token: string): Promise<ExecutiveDashboardData> {
  const [resources, findings, findingSummary, scoresLatest, scoreSummary, cloudAccounts] = await Promise.all([
    getResources(token),
    getFindings(token),
    getFindingsSummary(token),
    getScoresLatest(token),
    getScoresSummary(token),
    getCloudAccounts(token),
  ]);
  const scores = scoresLatest.items;
  const active = activeFindings(findings.items);
  const overallScore = buildDimensionScore("overall", "Overall Score", scores, scoreSummary);
  const dimensionScores = SCORE_ORDER.map(([key, label]) => buildDimensionScore(key, label, scores, scoreSummary));

  return {
    overall_score: overallScore,
    dimension_scores: dimensionScores,
    findings: {
      critical: findingSummary.by_severity.critical ?? 0,
      high: findingSummary.by_severity.high ?? 0,
      medium: findingSummary.by_severity.medium ?? 0,
      low: findingSummary.by_severity.low ?? 0,
      open: (findingSummary.by_status.open ?? 0) + (findingSummary.by_status.acknowledged ?? 0) || active.length,
      cloud_accounts: cloudAccounts.length,
      providers: uniqueProviders(cloudAccounts, resources),
    },
    inventory: {
      total_resources: resources.length,
      public_resources: countPublicResources(resources),
      untagged_resources: countUntaggedResources(resources),
    },
    risks: buildRisks(findings.items),
    last_collected_at: latestTimestamp(resources, scores),
    account_names: cloudAccounts.map((account) => account.name),
  };
}

function developmentFallback(): ExecutiveDashboardData {
  return {
    overall_score: {
      key: "overall",
      label: "Overall Score",
      score: 82,
      label_text: "Good",
      trend: "stable",
      top_driver: "Security and governance findings are the main operational drivers.",
    },
    dimension_scores: [
      { key: "finops", label: "FinOps", score: 78, label_text: "Good", trend: "improving", top_driver: "Unattached storage cleanup opportunity." },
      { key: "governance", label: "Governance", score: 64, label_text: "Fair", trend: "degrading", top_driver: "Missing ownership and cost center tags." },
      { key: "observability", label: "Observability", score: 71, label_text: "Fair", trend: "stable", top_driver: "Monitoring metadata gaps on production resources." },
      { key: "security_baseline", label: "Security", score: 86, label_text: "Good", trend: "stable", top_driver: "Public exposure findings require validation." },
      { key: "resilience", label: "Resilience", score: 84, label_text: "Good", trend: "unknown", top_driver: "Limited backup and recovery signals in current inventory." },
    ],
    findings: { critical: 2, high: 6, medium: 10, low: 4, open: 22, cloud_accounts: 2, providers: ["AWS", "OCI"] },
    inventory: { total_resources: 250, public_resources: 5, untagged_resources: 80 },
    risks: [
      { type: "public_exposure", label: "Public exposure", count: 5, severity: "critical" },
      { type: "missing_tags", label: "Missing tags", count: 80, severity: "high" },
      { type: "observability_gap", label: "Observability gaps", count: 14, severity: "medium" },
      { type: "unattached_volume", label: "Unattached volumes", count: 8, severity: "low" },
    ],
    last_collected_at: new Date().toISOString(),
    account_names: ["AWS Demo Account", "OCI Demo Tenancy"],
  };
}

export async function getExecutiveDashboard(token: string, tenantId?: string): Promise<ExecutiveDashboardData> {
  try {
    return await apiFetch<ExecutiveDashboardData>("/api/v1/dashboard/executive", {
      token,
      query: tenantId ? { tenant_id: tenantId } : undefined,
    });
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 404) {
      throw error;
    }
  }

  try {
    return await aggregateExecutiveDashboard(token);
  } catch (error) {
    if (process.env.NODE_ENV === "development") {
      return developmentFallback();
    }
    throw error;
  }
}
