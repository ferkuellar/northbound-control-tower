"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { formatDate, labelize } from "@/lib/formatters";
import type { Resource } from "@/lib/types";

type InventoryTableProps = {
  resources: Resource[];
};

function uniqueOptions(resources: Resource[], getValue: (resource: Resource) => string | null | undefined): string[] {
  return Array.from(new Set(resources.map(getValue).filter((value): value is string => Boolean(value)))).sort();
}

export function InventoryTable({ resources }: InventoryTableProps) {
  const [search, setSearch] = useState("");
  const [provider, setProvider] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");

  const providerOptions = uniqueOptions(resources, (resource) => resource.provider);
  const categoryOptions = uniqueOptions(resources, (resource) => resource.resource_category);
  const statusOptions = uniqueOptions(resources, (resource) => resource.lifecycle_status ?? resource.status);

  const needle = search.trim().toLowerCase();
  const filtered = resources.filter((resource) => {
    const matchesSearch =
      !needle ||
      [resource.name, resource.resource_id, resource.region, resource.owner]
        .filter((value): value is string => Boolean(value))
        .some((value) => value.toLowerCase().includes(needle));
    const matchesProvider = !provider || resource.provider === provider;
    const matchesCategory = !category || resource.resource_category === category;
    const currentStatus = resource.lifecycle_status ?? resource.status ?? "";
    const matchesStatus = !status || currentStatus === status;
    return matchesSearch && matchesProvider && matchesCategory && matchesStatus;
  });

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-ink">Inventory</h2>
            <p className="text-sm text-steel">{filtered.length} of {resources.length} normalized resources</p>
          </div>
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
            <Input placeholder="Search inventory" value={search} onChange={(event) => setSearch(event.target.value)} />
            <Select value={provider} onChange={(event) => setProvider(event.target.value)} aria-label="Provider filter">
              <option value="">All providers</option>
              {providerOptions.map((item) => (
                <option key={item} value={item}>{labelize(item)}</option>
              ))}
            </Select>
            <Select value={category} onChange={(event) => setCategory(event.target.value)} aria-label="Category filter">
              <option value="">All categories</option>
              {categoryOptions.map((item) => (
                <option key={item} value={item}>{labelize(item)}</option>
              ))}
            </Select>
            <Select value={status} onChange={(event) => setStatus(event.target.value)} aria-label="Status filter">
              <option value="">All statuses</option>
              {statusOptions.map((item) => (
                <option key={item} value={item}>{labelize(item)}</option>
              ))}
            </Select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {filtered.length === 0 ? (
          <EmptyState title="No resources found" description="Run an AWS or OCI inventory scan, or clear the active filters." />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-left text-xs font-semibold uppercase text-steel">
                <tr>
                  <th className="px-3 py-3">Provider</th>
                  <th className="px-3 py-3">Category</th>
                  <th className="px-3 py-3">Name</th>
                  <th className="px-3 py-3">Resource ID</th>
                  <th className="px-3 py-3">Region</th>
                  <th className="px-3 py-3">Lifecycle</th>
                  <th className="px-3 py-3">Exposure</th>
                  <th className="px-3 py-3">Environment</th>
                  <th className="px-3 py-3">Owner</th>
                  <th className="px-3 py-3">Last discovered</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((resource) => (
                  <tr key={resource.id} className="align-top hover:bg-slate-50">
                    <td className="px-3 py-3 font-medium uppercase text-ink">{resource.provider}</td>
                    <td className="px-3 py-3">{labelize(resource.resource_category)}</td>
                    <td className="px-3 py-3 font-medium text-ink">{resource.name ?? resource.resource_id}</td>
                    <td className="max-w-xs truncate px-3 py-3 text-steel" title={resource.resource_id}>{resource.resource_id}</td>
                    <td className="px-3 py-3">{resource.region ?? "Global"}</td>
                    <td className="px-3 py-3">{labelize(resource.lifecycle_status ?? resource.status)}</td>
                    <td className="px-3 py-3">
                      <Badge tone={resource.exposure_level === "public" ? "danger" : "neutral"}>{labelize(resource.exposure_level)}</Badge>
                    </td>
                    <td className="px-3 py-3">{labelize(resource.environment)}</td>
                    <td className="px-3 py-3">{resource.owner ?? "Unassigned"}</td>
                    <td className="px-3 py-3 text-steel">{formatDate(resource.discovered_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
