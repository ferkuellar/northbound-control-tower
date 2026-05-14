const commands = [
  ["nb help", "Show command reference"],
  ["nb status", "Check shell subsystems"],
  ["nb findings list", "List tenant findings"],
  ["nb findings show <finding_id>", "Inspect finding details"],
  ["nb fix suggest <finding_id>", "Generate safe remediation suggestion"],
  ["nb fix plan <finding_id>", "Create draft request stub"],
  ["nb requests list", "List draft requests"],
  ["nb evidence show <request_id>", "Show request evidence"],
];

export function CommandHelpPanel() {
  return (
    <section className="rounded-2xl border border-northbound-border bg-northbound-panel p-4">
      <h2 className="text-sm font-semibold text-northbound-text">Allowed Commands</h2>
      <p className="mt-1 text-xs text-northbound-textMuted">Only registered `nb` commands execute. OS shell access is blocked.</p>
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

