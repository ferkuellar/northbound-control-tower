export default function DashboardLoading() {
  return (
    <main className="min-h-screen bg-northbound-bg p-4 text-northbound-text">
      <div className="flex min-h-[calc(100vh-2rem)] overflow-hidden rounded-2xl border border-northbound-border">
        <aside className="hidden w-60 border-r border-northbound-border bg-northbound-bg p-4 md:block">
          <div className="h-10 rounded-lg bg-northbound-panel" />
          <div className="mt-8 space-y-2">
            {Array.from({ length: 8 }).map((_, index) => (
              <div key={index} className="h-8 rounded-lg bg-northbound-panel" />
            ))}
          </div>
        </aside>
        <section className="flex-1 bg-northbound-bg">
          <div className="border-b border-northbound-border p-4">
            <div className="h-5 w-56 rounded bg-northbound-panel" />
            <div className="mt-2 h-3 w-96 max-w-full rounded bg-northbound-border" />
          </div>
          <div className="space-y-4 p-4">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <div key={index} className="h-40 rounded-2xl border border-northbound-border bg-northbound-panel" />
              ))}
            </div>
            <div className="grid gap-2 lg:grid-cols-5">
              {Array.from({ length: 5 }).map((_, index) => (
                <div key={index} className="h-20 rounded-xl border border-northbound-border bg-northbound-panel" />
              ))}
            </div>
            <div className="grid gap-3 xl:grid-cols-2">
              <div className="h-48 rounded-2xl border border-northbound-border bg-northbound-panel" />
              <div className="h-48 rounded-2xl border border-northbound-border bg-northbound-panel" />
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
