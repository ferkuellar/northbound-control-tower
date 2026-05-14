export type AdminTenant = {
  id: string;
  name: string;
  slug: string;
  status: "active" | "inactive" | string;
  industry: string | null;
  contact_name: string | null;
  contact_email: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  cloud_accounts_count: number;
  resources_count: number;
  open_findings_count: number;
  latest_score: number | null;
};

export type AdminTenantCreate = {
  name: string;
  slug: string;
  industry?: string;
  contact_name?: string;
  contact_email?: string;
  notes?: string;
};

export type CostServiceBreakdown = {
  id: string;
  service_name: string;
  monthly_cost: number;
  percentage: number;
};

export type CostRecommendation = {
  id: string;
  priority: number;
  title: string;
  description: string;
  service_name: string;
  estimated_savings_percent: number;
  estimated_monthly_savings: number;
  estimated_annual_savings: number;
  implementation_effort: string;
  risk_level: string;
  assumptions: string;
};

export type CostOptimizationResponse = {
  tenant_id: string;
  tenant_name: string;
  case: {
    id: string;
    provider: string;
    monthly_spend: number;
    currency: string;
    description: string;
    service_breakdown: CostServiceBreakdown[];
    recommendations: CostRecommendation[];
  };
  estimated_monthly_savings: number;
  estimated_annual_savings: number;
  optimized_monthly_cost: number;
  architecture_current: string[];
  architecture_proposed: string[];
  implementation_plan: string[];
};
