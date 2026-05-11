import type { ReactNode } from "react";

type EmptyStateProps = {
  title: string;
  description?: string;
  children?: ReactNode;
};

export function EmptyState({ title, description, children }: EmptyStateProps) {
  return (
    <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-5 py-8 text-center">
      <p className="text-sm font-semibold text-ink">{title}</p>
      {description ? <p className="mt-1 text-sm text-steel">{description}</p> : null}
      {children ? <div className="mt-4">{children}</div> : null}
    </div>
  );
}
