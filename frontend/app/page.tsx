import { Activity, Cloud, Gauge, ShieldAlert } from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const scopeItems = [
  { label: "Clouds", value: "AWS, OCI", icon: Cloud },
  { label: "Findings", value: "5 deterministic checks", icon: ShieldAlert },
  { label: "Architecture", value: "Modular monolith", icon: Gauge },
  { label: "Telemetry", value: "Prometheus ready", icon: Activity },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-surface">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-xl font-semibold tracking-normal text-ink">Northbound Control Tower</h1>
            <p className="text-sm text-steel">Enterprise multicloud operational intelligence</p>
          </div>
          <div className="rounded-md border border-slate-200 px-3 py-2 text-sm text-steel">
            API: {API_BASE_URL}
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-6 py-8">
        <div className="grid gap-4 md:grid-cols-4">
          {scopeItems.map((item) => {
            const Icon = item.icon;
            return (
              <article key={item.label} className="rounded-md border border-slate-200 bg-white p-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-md bg-teal-50 text-signal">
                    <Icon size={20} aria-hidden="true" />
                  </div>
                  <div>
                    <p className="text-sm text-steel">{item.label}</p>
                    <p className="text-base font-semibold text-ink">{item.value}</p>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </main>
  );
}
