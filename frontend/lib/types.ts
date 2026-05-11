export type UserRole = "ADMIN" | "ANALYST" | "VIEWER";

export type User = {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string;
  role: UserRole;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};

export type CloudAccount = {
  id: string;
  tenant_id: string;
  provider: "aws" | "oci" | string;
  name: string;
  account_id: string | null;
  auth_type: string;
  role_arn: string | null;
  external_id: string | null;
  default_region: string;
  region: string | null;
  compartment_ocid: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type Resource = {
  id: string;
  tenant_id: string;
  cloud_account_id: string;
  provider: "aws" | "oci" | string;
  resource_category: string;
  resource_type: string;
  resource_id: string;
  fingerprint: string | null;
  name: string | null;
  region: string | null;
  account_id: string | null;
  compartment_id: string | null;
  availability_zone: string | null;
  availability_domain: string | null;
  raw_type: string | null;
  status: string | null;
  lifecycle_status: string | null;
  exposure_level: string | null;
  environment: string | null;
  criticality: string | null;
  owner: string | null;
  cost_center: string | null;
  application: string | null;
  service_name: string | null;
  tags: Record<string, unknown>;
  metadata_json: Record<string, unknown>;
  relationships: Record<string, unknown> | Array<Record<string, unknown>>;
  discovered_at: string;
  created_at: string;
  updated_at: string;
};

export type FindingSeverity = "critical" | "high" | "medium" | "low" | "informational";
export type FindingStatus = "open" | "acknowledged" | "resolved" | "false_positive";

export type Finding = {
  id: string;
  tenant_id: string;
  cloud_account_id: string;
  resource_id: string | null;
  provider: "aws" | "oci" | string;
  finding_type: string;
  category: string;
  severity: FindingSeverity;
  status: FindingStatus;
  title: string;
  description: string;
  evidence: Record<string, unknown>;
  recommendation: string;
  estimated_monthly_waste: number | null;
  rule_id: string;
  fingerprint: string;
  first_seen_at: string;
  last_seen_at: string;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
};

export type FindingListResponse = {
  items: Finding[];
  total: number;
};

export type FindingSummary = {
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
  by_category: Record<string, number>;
  by_provider: Record<string, number>;
  by_status: Record<string, number>;
};

export type ScoreType =
  | "finops"
  | "governance"
  | "observability"
  | "security_baseline"
  | "resilience"
  | "overall";

export type CloudScore = {
  id: string;
  tenant_id: string;
  cloud_account_id: string | null;
  provider: string | null;
  score_type: ScoreType;
  score_value: number;
  grade: string;
  trend: string;
  summary: string;
  evidence: Record<string, unknown>;
  calculated_at: string;
  created_at: string;
  updated_at: string;
};

export type ScoreLatestResponse = {
  items: CloudScore[];
};

export type ScoreHistoryResponse = {
  items: CloudScore[];
  total: number;
};

export type ScoreSummary = {
  overall_score: number | null;
  domain_scores: Record<string, number>;
  grades: Record<string, string>;
  trends: Record<string, string>;
  top_drivers: Array<Record<string, unknown>>;
  counts_by_severity: Record<string, number>;
};

export type DashboardData = {
  user: User;
  resources: Resource[];
  findings: FindingListResponse;
  findingSummary: FindingSummary;
  scoresLatest: ScoreLatestResponse;
  scoreSummary: ScoreSummary;
  scoreHistory: ScoreHistoryResponse;
  cloudAccounts: CloudAccount[];
};
