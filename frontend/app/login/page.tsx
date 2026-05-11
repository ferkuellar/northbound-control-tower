"use client";

import { Activity, LogIn } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { ApiError, API_BASE_URL, getCurrentUser, login } from "@/lib/api";
import { getToken, setStoredUser, setToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (token) {
      router.replace("/dashboard");
    }
  }, [router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const token = await login(email, password);
      setToken(token);
      const user = await getCurrentUser(token.access_token);
      setStoredUser(user);
      router.replace("/dashboard");
    } catch (requestError) {
      const message =
        requestError instanceof ApiError || requestError instanceof Error ? requestError.message : "Login failed";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen bg-surface lg:grid-cols-[1fr_440px]">
      <section className="hidden border-r border-slate-200 bg-white px-10 py-12 lg:flex lg:flex-col lg:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-md bg-teal-50 text-signal">
              <Activity size={22} aria-hidden="true" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-ink">Northbound Control Tower</h1>
              <p className="text-sm text-steel">Executive cloud operations dashboard</p>
            </div>
          </div>
          <div className="mt-16 max-w-2xl">
            <p className="text-3xl font-semibold leading-tight tracking-normal text-ink">
              Unified scores, findings, inventory, risks, and trends for AWS and OCI.
            </p>
            <p className="mt-4 text-base text-steel">
              Deterministic backend APIs power this Phase 8 frontend foundation.
            </p>
          </div>
        </div>
        <div className="rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-steel">
          API base URL: <span className="font-medium text-ink">{API_BASE_URL}</span>
        </div>
      </section>

      <section className="flex items-center justify-center px-4 py-10">
        <Card className="w-full max-w-md">
          <CardHeader>
            <h2 className="text-xl font-semibold text-ink">Sign in</h2>
            <p className="mt-1 text-sm text-steel">Use the Phase 2 admin, analyst, or viewer account.</p>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div className="space-y-2">
                <label className="text-sm font-medium text-ink" htmlFor="email">Email</label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-ink" htmlFor="password">Password</label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </div>
              {error ? (
                <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-risk">{error}</div>
              ) : null}
              <Button className="w-full" type="submit" disabled={isSubmitting}>
                <LogIn size={16} aria-hidden="true" />
                {isSubmitting ? "Signing in" : "Sign in"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
