"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Select } from "@/components/ui/Select";
import { formatDate, labelize } from "@/lib/formatters";
import type { Finding } from "@/lib/types";

type FindingsTableProps = {
  findings: Finding[];
};

function severityTone(severity: string): "danger" | "warning" | "info" | "neutral" {
  if (severity === "critical" || severity === "high") {
    return "danger";
  }
  if (severity === "medium") {
    return "warning";
  }
  if (severity === "low") {
    return "info";
  }
  return "neutral";
}

function statusTone(status: string): "success" | "warning" | "neutral" {
  if (status === "resolved") {
    return "success";
  }
  if (status === "acknowledged") {
    return "warning";
  }
  return "neutral";
}

function uniqueOptions(findings: Finding[], getValue: (finding: Finding) => string): string[] {
  return Array.from(new Set(findings.map(getValue))).sort();
}

export function FindingsTable({ findings }: FindingsTableProps) {
  const [severity, setSeverity] = useState("");
  const [category, setCategory] = useState("");
  const [provider, setProvider] = useState("");
  const [status, setStatus] = useState("");
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);

  const filtered = findings.filter(
    (finding) =>
      (!severity || finding.severity === severity) &&
      (!category || finding.category === category) &&
      (!provider || finding.provider === provider) &&
      (!status || finding.status === status),
  );

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-northbound-white100">Findings</h2>
            <p className="text-sm text-northbound-white60">{filtered.length} of {findings.length} deterministic findings</p>
          </div>
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
            <Select value={severity} onChange={(event) => setSeverity(event.target.value)} aria-label="Severity filter">
              <option value="">All severities</option>
              {uniqueOptions(findings, (finding) => finding.severity).map((item) => (
                <option key={item} value={item}>{labelize(item)}</option>
              ))}
            </Select>
            <Select value={category} onChange={(event) => setCategory(event.target.value)} aria-label="Category filter">
              <option value="">All categories</option>
              {uniqueOptions(findings, (finding) => finding.category).map((item) => (
                <option key={item} value={item}>{labelize(item)}</option>
              ))}
            </Select>
            <Select value={provider} onChange={(event) => setProvider(event.target.value)} aria-label="Provider filter">
              <option value="">All providers</option>
              {uniqueOptions(findings, (finding) => finding.provider).map((item) => (
                <option key={item} value={item}>{labelize(item)}</option>
              ))}
            </Select>
            <Select value={status} onChange={(event) => setStatus(event.target.value)} aria-label="Status filter">
              <option value="">All statuses</option>
              {uniqueOptions(findings, (finding) => finding.status).map((item) => (
                <option key={item} value={item}>{labelize(item)}</option>
              ))}
            </Select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {filtered.length === 0 ? (
          <EmptyState title="No findings found" description="Run the findings engine, or clear the active filters." />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-northbound-black80 text-sm text-northbound-white80">
              <thead className="bg-northbound-black100/60 text-left text-xs font-semibold uppercase text-northbound-white60">
                <tr>
                  <th className="px-3 py-3">Severity</th>
                  <th className="px-3 py-3">Type</th>
                  <th className="px-3 py-3">Category</th>
                  <th className="px-3 py-3">Provider</th>
                  <th className="px-3 py-3">Resource</th>
                  <th className="px-3 py-3">Title</th>
                  <th className="px-3 py-3">Status</th>
                  <th className="px-3 py-3">Last seen</th>
                  <th className="px-3 py-3">Detail</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {filtered.map((finding) => (
                  <tr key={finding.id} className="align-top hover:bg-northbound-black100/45">
                    <td className="px-3 py-3"><Badge tone={severityTone(finding.severity)}>{labelize(finding.severity)}</Badge></td>
                    <td className="px-3 py-3">{labelize(finding.finding_type)}</td>
                    <td className="px-3 py-3">{labelize(finding.category)}</td>
                    <td className="px-3 py-3 font-medium uppercase">{finding.provider}</td>
                    <td className="max-w-[10rem] truncate px-3 py-3 text-northbound-white60">{finding.resource_id ?? "Tenant scope"}</td>
                    <td className="max-w-md px-3 py-3 font-medium text-northbound-white100">{finding.title}</td>
                    <td className="px-3 py-3"><Badge tone={statusTone(finding.status)}>{labelize(finding.status)}</Badge></td>
                    <td className="px-3 py-3 text-northbound-white60">{formatDate(finding.last_seen_at)}</td>
                    <td className="px-3 py-3">
                      <Button variant="ghost" className="h-8 px-2" onClick={() => setSelectedFinding(finding)}>Open</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {selectedFinding ? (
          <div className="fixed inset-0 z-30 bg-northbound-black100/85 p-4" role="dialog" aria-modal="true">
            <div className="ml-auto h-full max-w-2xl overflow-y-auto rounded-lg border border-northbound-black80 bg-northbound-black90 shadow-2xl">
              <div className="flex items-start justify-between border-b border-white/10 px-5 py-4">
                <div>
                  <h3 className="text-lg font-semibold text-northbound-white100">{selectedFinding.title}</h3>
                  <p className="text-sm text-northbound-white60">{selectedFinding.rule_id}</p>
                </div>
                <Button variant="secondary" onClick={() => setSelectedFinding(null)}>Close</Button>
              </div>
              <div className="space-y-5 p-5">
                <div className="flex flex-wrap gap-2">
                  <Badge tone={severityTone(selectedFinding.severity)}>{labelize(selectedFinding.severity)}</Badge>
                  <Badge>{labelize(selectedFinding.category)}</Badge>
                  <Badge>{selectedFinding.provider.toUpperCase()}</Badge>
                  <Badge tone={statusTone(selectedFinding.status)}>{labelize(selectedFinding.status)}</Badge>
                </div>
                <section>
                  <h4 className="text-sm font-semibold text-northbound-white100">Description</h4>
                  <p className="mt-2 text-sm text-northbound-white60">{selectedFinding.description}</p>
                </section>
                <section>
                  <h4 className="text-sm font-semibold text-northbound-white100">Recommendation</h4>
                  <p className="mt-2 text-sm text-northbound-white60">{selectedFinding.recommendation}</p>
                </section>
                <section>
                  <h4 className="text-sm font-semibold text-northbound-white100">Evidence</h4>
                  <pre className="mt-2 max-h-80 overflow-auto rounded-md border border-northbound-black80 bg-northbound-black100 p-4 text-xs text-northbound-white80">
                    {JSON.stringify(selectedFinding.evidence, null, 2)}
                  </pre>
                </section>
              </div>
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
