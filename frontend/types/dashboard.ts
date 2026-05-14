export type ScoreTrend = "improving" | "stable" | "declining" | "degrading" | "unknown";
export type ScoreLabel = "Excellent" | "Good" | "Fair" | "Poor" | "Critical";

export interface DimensionScore {
  key: string;
  label: string;
  score: number;
  label_text: ScoreLabel;
  trend: ScoreTrend;
  top_driver: string | null;
}

export interface FindingsSummary {
  critical: number;
  high: number;
  medium: number;
  low?: number;
  open: number;
  cloud_accounts: number;
  providers: string[];
}

export interface InventorySummary {
  total_resources: number;
  public_resources: number;
  untagged_resources: number;
}

export interface RiskItem {
  type: string;
  label: string;
  count: number;
  severity: "critical" | "high" | "medium" | "low";
}

export interface ExecutiveDashboardData {
  tenant?: {
    id: string;
    name: string;
    slug: string;
    industry?: string | null;
  };
  cloud_accounts?: Array<{
    id: string;
    name: string;
    provider: string;
    account_id: string | null;
    default_region: string;
  }>;
  overall_score: DimensionScore;
  dimension_scores: DimensionScore[];
  findings: FindingsSummary;
  inventory: InventorySummary;
  risks: RiskItem[];
  last_collected_at: string;
  account_names: string[];
}
