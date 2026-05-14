import { ShieldAlert } from "lucide-react";

type ErrorStateProps = {
  title?: string;
  message: string;
  onRetry?: () => void;
};

export function ErrorState({ title = "Dashboard unavailable", message, onRetry }: ErrorStateProps) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-northbound-bg px-4 text-northbound-text">
      <section className="w-full max-w-lg rounded-2xl border border-red-500/30 bg-northbound-panel p-6 shadow-[0_16px_48px_rgba(0,0,0,0.28)]">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-red-500/30 bg-red-950/40 text-red-200">
            <ShieldAlert size={20} aria-hidden="true" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-northbound-text">{title}</h1>
            <p className="mt-2 text-sm leading-6 text-northbound-textMuted">{message}</p>
          </div>
        </div>
        {onRetry ? (
          <button
            type="button"
            onClick={onRetry}
            className="mt-5 rounded-lg border border-northbound-border bg-northbound-bg px-4 py-2 text-sm font-medium text-northbound-textSecondary transition hover:border-northbound-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-northbound-white80"
          >
            Retry
          </button>
        ) : null}
      </section>
    </main>
  );
}
