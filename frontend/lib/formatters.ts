import type { CloudScore, Finding, FindingSeverity, Resource } from "./types";

export const scoreLabels: Record<string, string> = {
  overall: "Overall Cloud Operational Score",
  finops: "FinOps",
  governance: "Governance",
  observability: "Observability",
  security_baseline: "Security Baseline",
  resilience: "Resilience",
};

export const severityOrder: Record<FindingSeverity, number> = {
  critical: 5,
  high: 4,
  medium: 3,
  low: 2,
  informational: 1,
};

export function labelize(value: string | null | undefined): string {
  if (!value) {
    return "Unknown";
  }
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Unknown";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function scoreByType(scores: CloudScore[]): Map<string, CloudScore> {
  return new Map(scores.map((score) => [score.score_type, score]));
}

export function openFindings(findings: Finding[]): Finding[] {
  return findings.filter((finding) => finding.status === "open" || finding.status === "acknowledged");
}

export function topRiskFindings(findings: Finding[], limit = 10): Finding[] {
  return [...findings]
    .sort((left, right) => {
      const severityDelta = severityOrder[right.severity] - severityOrder[left.severity];
      if (severityDelta !== 0) {
        return severityDelta;
      }
      return new Date(right.last_seen_at).getTime() - new Date(left.last_seen_at).getTime();
    })
    .slice(0, limit);
}

export function countBy<T>(items: T[], getKey: (item: T) => string | null | undefined): Record<string, number> {
  return items.reduce<Record<string, number>>((accumulator, item) => {
    const key = getKey(item) ?? "unknown";
    accumulator[key] = (accumulator[key] ?? 0) + 1;
    return accumulator;
  }, {});
}

export function countPublicResources(resources: Resource[]): number {
  return resources.filter((resource) => resource.exposure_level === "public").length;
}

export function countUntaggedResources(resources: Resource[]): number {
  return resources.filter(
    (resource) =>
      !resource.environment ||
      resource.environment === "unknown" ||
      !resource.owner ||
      !resource.cost_center ||
      !resource.application,
  ).length;
}
