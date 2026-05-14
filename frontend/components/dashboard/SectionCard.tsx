import type { CSSProperties, ReactNode } from "react";

type SectionCardProps = {
  id?: string;
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
};

export function SectionCard({ id, children, className = "", style }: SectionCardProps) {
  return (
    <section
      id={id}
      style={style}
      className={`rounded-2xl border border-northbound-border bg-northbound-panel shadow-[0_16px_48px_rgba(0,0,0,0.22)] transition-colors hover:border-northbound-hover ${className}`}
    >
      {children}
    </section>
  );
}
