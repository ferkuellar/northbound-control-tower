export function EvidencePanel() {
  return (
    <section className="rounded-2xl border border-northbound-border bg-northbound-panel p-4">
      <h2 className="text-sm font-semibold text-northbound-text">Security Boundary</h2>
      <ul className="mt-3 space-y-2 text-xs text-northbound-textMuted">
        <li>No `/bin/bash`, PowerShell or arbitrary OS commands.</li>
        <li>No Terraform destroy or apply auto-approve.</li>
        <li>No cloud credentials, JWTs or `.env` values printed.</li>
        <li>AI cannot execute or approve infrastructure changes.</li>
      </ul>
    </section>
  );
}

