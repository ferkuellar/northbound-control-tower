export function FindingContextPanel() {
  return (
    <section className="rounded-2xl border border-northbound-border bg-northbound-panel p-4">
      <h2 className="text-sm font-semibold text-northbound-text">Operational Context</h2>
      <div className="mt-4 grid gap-3">
        <div className="rounded-xl border border-[#BA7517]/40 bg-[#BA7517]/10 p-3">
          <p className="text-xs font-semibold text-[#F5D39F]">Terraform</p>
          <p className="mt-1 text-xs text-northbound-textMuted">Validate, plan and apply commands are recognized but disabled in this phase.</p>
        </div>
        <div className="rounded-xl border border-[#1D9E75]/40 bg-[#1D9E75]/10 p-3">
          <p className="text-xs font-semibold text-[#9FE1CB]">Audit</p>
          <p className="mt-1 text-xs text-northbound-textMuted">Every command is persisted with role, status, duration and safe output.</p>
        </div>
      </div>
    </section>
  );
}

