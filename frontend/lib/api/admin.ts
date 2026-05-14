import { apiFetch, API_BASE_URL } from "@/lib/api";
import type { AdminTenant, AdminTenantCreate, CostOptimizationResponse } from "@/types/admin";

export function listAdminTenants(token: string): Promise<AdminTenant[]> {
  return apiFetch<AdminTenant[]>("/api/v1/admin/tenants", { token });
}

export function createAdminTenant(token: string, payload: AdminTenantCreate): Promise<AdminTenant> {
  return apiFetch<AdminTenant>("/api/v1/admin/tenants", {
    method: "POST",
    token,
    body: payload,
  });
}

export function getAdminTenant(token: string, tenantId: string): Promise<AdminTenant> {
  return apiFetch<AdminTenant>(`/api/v1/admin/tenants/${tenantId}`, { token });
}

export function seedClaraDemo(token: string): Promise<CostOptimizationResponse> {
  return apiFetch<CostOptimizationResponse>("/api/v1/cost-optimization/demo/clara", {
    method: "POST",
    token,
  });
}

export function getCostOptimization(token: string, tenantId: string): Promise<CostOptimizationResponse> {
  return apiFetch<CostOptimizationResponse>(`/api/v1/cost-optimization/${tenantId}`, { token });
}

export function costCsvUrl(tenantId: string): string {
  return `${API_BASE_URL}/api/v1/cost-optimization/${tenantId}/export.csv`;
}
