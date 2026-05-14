const commands = [
  ["nb help", "Show command reference"],
  ["nb status", "Check shell subsystems"],
  ["nb findings list", "List tenant findings"],
  ["nb findings show <finding_id>", "Inspect finding details"],
  ["nb fix suggest <finding_id>", "Generate safe remediation suggestion"],
  ["nb fix plan <finding_id>", "Create draft request stub"],
  ["nb requests list", "List draft requests"],
  ["nb evidence show <request_id>", "Show request evidence"],
  ["nb security scan <request_id>", "Run Checkov gates"],
  ["nb cost estimate <request_id>", "Estimate monthly cost"],
  ["nb risk summary <request_id>", "Generate risk packet"],
  ["nb gates evaluate <request_id>", "Decide readiness"],
];

export function CommandHelpPanel() {
  return (
    <section className="rounded-2xl border border-northbound-border bg-northbound-panel p-4">
      <h2 className="text-sm font-semibold text-northbound-text">Allowed Commands</h2>
      <p className="mt-1 text-xs text-northbound-textMuted">Only registered `nb` commands execute. OS shell access is blocked.</p>
      <div className="mt-3 grid grid-cols-2 gap-2 text-[11px]">
        <span className="rounded border border-[#4CA883]/40 px-2 py-1 text-[#9FE1CB]">Security Gates: Enabled</span>
        <span className="rounded border border-[#4CA883]/40 px-2 py-1 text-[#9FE1CB]">Cost Estimation: Enabled</span>
        <span className="rounded border border-[#E8B84E]/40 px-2 py-1 text-[#F3D48A]">Apply: Disabled</span>
        <span className="rounded border border-[#A32D2D]/40 px-2 py-1 text-[#F2A0A0]">Destroy: Blocked</span>
      </div>
      <div className="mt-4 space-y-2">
        {commands.map(([command, description]) => (
          <div key={command} className="rounded-xl border border-white/10 bg-northbound-bg px-3 py-2">
            <code className="text-xs text-[#9FE1CB]">{command}</code>
            <p className="mt-1 text-xs text-northbound-textMuted">{description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

