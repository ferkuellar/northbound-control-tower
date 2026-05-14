"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { createAdminTenant, listAdminTenants, seedClaraDemo } from "@/lib/api/admin";
import { ApiError, getCurrentUser } from "@/lib/api";
import { clearSession, getToken, setStoredUser } from "@/lib/auth";
import type { User } from "@/lib/types";
import type { AdminTenant } from "@/types/admin";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; user: User; tenants: AdminTenant[] };

export default function ClientsAdminPage() {
  const router = useRouter();
  const [state, setState] = useState<State>({ status: "loading" });
  const [form, setForm] = useState({ name: "", slug: "", industry: "", contact_name: "", contact_email: "", notes: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const load = useCallback(async () => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    try {
      const user = await getCurrentUser(token);
      if (user.role !== "ADMIN") {
        setState({ status: "error", message: "Only ADMIN users can manage clients." });
        return;
      }
      const tenants = await listAdminTenants(token);
      setStoredUser(user);
      setState({ status: "ready", user, tenants });
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        clearSession();
        router.replace("/login");
        return;
      }
      setState({ status: "error", message: error instanceof Error ? error.message : "Clients unavailable" });
    }
  }, [router]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = getToken();
    if (!token) return;
    setIsSubmitting(true);
    try {
      await createAdminTenant(token, {
        name: form.name,
        slug: form.slug,
        industry: form.industry || undefined,
        contact_name: form.contact_name || undefined,
        contact_email: form.contact_email || undefined,
        notes: form.notes || undefined,
      });
      setForm({ name: "", slug: "", industry: "", contact_name: "", contact_email: "", notes: "" });
      await load();
    } finally {
      setIsSubmitting(false);
    }
  }

  async function seedClara() {
    const token = getToken();
    if (!token) return;
    await seedClaraDemo(token);
    await load();
  }

  if (state.status === "loading") return null;

  const user = state.status === "ready" ? state.user : null;
  const tenants = state.status === "ready" ? state.tenants : [];

  return (
    <main className="min-h-screen bg-northbound-bg p-3 text-northbound-text">
      <div className="flex min-h-[calc(100vh-1.5rem)] flex-col overflow-hidden rounded-2xl border border-northbound-border md:flex-row">
        <Sidebar user={user} />
        <section className="flex min-w-0 flex-1 flex-col bg-northbound-bg">
          <TopBar cloudAccountsCount={0} providers={[]} tenantName="Client Administration" selectedScope="All clients" />
          <div className="grid gap-4 p-4 xl:grid-cols-[380px_1fr]">
            <Card>
              <CardHeader>
                <h1 className="text-lg font-semibold text-northbound-text">Create client</h1>
                <p className="text-sm text-northbound-textMuted">Register tenants for managed cloud operations.</p>
              </CardHeader>
              <CardContent>
                <form className="space-y-3" onSubmit={submit}>
                  <Input required placeholder="Client name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
                  <Input required placeholder="slug-example" value={form.slug} onChange={(event) => setForm({ ...form, slug: event.target.value })} />
                  <Input placeholder="Industry" value={form.industry} onChange={(event) => setForm({ ...form, industry: event.target.value })} />
                  <Input placeholder="Contact name" value={form.contact_name} onChange={(event) => setForm({ ...form, contact_name: event.target.value })} />
                  <Input placeholder="Contact email" value={form.contact_email} onChange={(event) => setForm({ ...form, contact_email: event.target.value })} />
                  <Input placeholder="Notes" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
                  <Button className="w-full" disabled={isSubmitting} type="submit">{isSubmitting ? "Creating" : "Create Client"}</Button>
                </form>
                <Button className="mt-3 w-full" variant="secondary" onClick={() => void seedClara()}>
                  Seed Clara Fintech Demo
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <h2 className="text-lg font-semibold text-northbound-text">Clients</h2>
                <p className="text-sm text-northbound-textMuted">{tenants.length} tenants registered</p>
              </CardHeader>
              <CardContent>
                {state.status === "error" ? (
                  <p className="text-sm text-red-200">{state.message}</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-northbound-border text-sm text-northbound-textSecondary">
                      <thead className="text-left text-xs uppercase text-northbound-textMuted">
                        <tr>
                          <th className="px-3 py-2">Client</th>
                          <th className="px-3 py-2">Status</th>
                          <th className="px-3 py-2">Accounts</th>
                          <th className="px-3 py-2">Resources</th>
                          <th className="px-3 py-2">Findings</th>
                          <th className="px-3 py-2">Score</th>
                          <th className="px-3 py-2">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/10">
                        {tenants.map((tenant) => (
                          <tr key={tenant.id} className="hover:bg-northbound-bg">
                            <td className="px-3 py-3">
                              <p className="font-semibold text-northbound-text">{tenant.name}</p>
                              <p className="text-xs text-northbound-textMuted">{tenant.slug} · {tenant.industry ?? "No industry"}</p>
                            </td>
                            <td className="px-3 py-3">{tenant.status}</td>
                            <td className="px-3 py-3">{tenant.cloud_accounts_count}</td>
                            <td className="px-3 py-3">{tenant.resources_count}</td>
                            <td className="px-3 py-3">{tenant.open_findings_count}</td>
                            <td className="px-3 py-3">{tenant.latest_score ?? "N/A"}</td>
                            <td className="px-3 py-3">
                              <Button variant="secondary" onClick={() => router.push(`/clients/${tenant.id}/cost-optimization`)}>
                                Cost View
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </section>
      </div>
    </main>
  );
}
