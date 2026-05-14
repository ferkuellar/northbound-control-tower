import type { ReactNode } from "react";

type EmptyStateProps = {
  title: string;
  description?: string;
  children?: ReactNode;
};

export function EmptyState({ title, description, children }: EmptyStateProps) {
  return (
    <div className="rounded-md border border-dashed border-northbound-black80 bg-northbound-black100 px-5 py-8 text-center">
      <p className="text-sm font-semibold text-northbound-white100">{title}</p>
      {description ? <p className="mt-1 text-sm text-northbound-white60">{description}</p> : null}
      {children ? <div className="mt-4">{children}</div> : null}
    </div>
  );
}
