import { apiFetch, API_BASE_URL } from "@/lib/api";

export type ReportArtifact = {
  id: string;
  tenant_id: string;
  report_type: string;
  report_format: string;
  title: string;
  created_at: string;
};

type ReportGenerateResponse = {
  report: ReportArtifact;
};

type ReportListResponse = {
  items: ReportArtifact[];
  total: number;
};

export function generateReport(
  token: string,
  reportType: "executive" | "technical",
  reportFormat: "pdf" | "html",
  tenantId?: string,
): Promise<ReportArtifact> {
  return apiFetch<ReportGenerateResponse>("/api/v1/reports/generate", {
    method: "POST",
    token,
    body: {
      report_type: reportType,
      report_format: reportFormat,
      tenant_id: tenantId,
      branding: {
        company_name: "Northbound Control Tower",
        primary_color: "#0A0E15",
        secondary_color: "#373F4E",
      },
    },
  }).then((response) => response.report);
}

export function listReports(token: string, tenantId?: string): Promise<ReportArtifact[]> {
  return apiFetch<ReportListResponse>("/api/v1/reports", {
    token,
    query: tenantId ? { tenant_id: tenantId } : undefined,
  }).then((response) => response.items);
}

export function reportPreviewUrl(reportId: string): string {
  return `${API_BASE_URL}/api/v1/reports/${reportId}/preview`;
}

export function reportDownloadUrl(reportId: string): string {
  return `${API_BASE_URL}/api/v1/reports/${reportId}/download`;
}

async function fetchReportArtifact(token: string, url: string): Promise<Response> {
  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    throw new Error("Report artifact unavailable");
  }
  return response;
}

export async function downloadReportArtifact(token: string, report: ReportArtifact): Promise<void> {
  const response = await fetchReportArtifact(token, reportDownloadUrl(report.id));
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const extension = report.report_format === "html" ? "html" : "pdf";
  link.href = url;
  link.download = `${report.report_type}-${report.id}.${extension}`;
  link.click();
  URL.revokeObjectURL(url);
}

export async function openReportPreview(token: string, report: ReportArtifact, print = false): Promise<void> {
  const response = await fetchReportArtifact(token, reportPreviewUrl(report.id));
  const html = await response.text();
  const blob = new Blob([html], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  const win = window.open(url, "_blank", "noopener,noreferrer");
  if (print && win) {
    window.setTimeout(() => win.print(), 700);
  }
  window.setTimeout(() => URL.revokeObjectURL(url), 30000);
}
