"use client";

import { LogIn } from "lucide-react";
import Image from "next/image";
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
    <main className="grid min-h-screen bg-northbound-black100 text-northbound-white100 lg:grid-cols-[1fr_440px]">
      <section className="hidden border-r border-northbound-black90 bg-northbound-black100 px-10 py-12 lg:flex lg:flex-col lg:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-white/10 bg-northbound-black90 p-1.5">
              <Image src="/brand/logo-northbound.png" alt="Northbound logo" width={44} height={44} className="h-full w-full object-contain" priority />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-northbound-white100">Northbound Control Tower</h1>
              <p className="text-sm text-northbound-white60">Executive cloud operations dashboard</p>
            </div>
          </div>
          <div className="mt-16 max-w-2xl">
            <p className="text-3xl font-semibold leading-tight tracking-normal text-northbound-white100">
              Unified scores, findings, inventory, risks, and trends for AWS and OCI.
            </p>
            <p className="mt-4 text-base text-northbound-white80">
              Deterministic backend APIs power this Phase 8 frontend foundation.
            </p>
          </div>
        </div>
        <div className="rounded-md border border-northbound-black80 bg-northbound-black90 px-4 py-3 text-sm text-northbound-white60">
          API base URL: <span className="font-medium text-northbound-white100">{API_BASE_URL}</span>
        </div>
      </section>

      <section className="flex items-center justify-center px-4 py-10">
        <Card className="w-full max-w-md">
          <CardHeader>
            <div className="mb-4 flex justify-center lg:hidden">
              <Image src="/brand/logo-northbound.png" alt="Northbound logo" width={48} height={48} className="h-12 w-12 object-contain" priority />
            </div>
            <h2 className="text-xl font-semibold text-northbound-white100">Sign in</h2>
            <p className="mt-1 text-sm text-northbound-white60">Use the Phase 2 admin, analyst, or viewer account.</p>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div className="space-y-2">
                <label className="text-sm font-medium text-northbound-white80" htmlFor="email">Email</label>
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
                <label className="text-sm font-medium text-northbound-white80" htmlFor="password">Password</label>
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
                <div className="rounded-md border border-red-500/40 bg-red-950/40 px-3 py-2 text-sm text-red-200">{error}</div>
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
