import type { ReactNode } from "react";

type CardProps = {
  children: ReactNode;
  className?: string;
};

export function Card({ children, className = "" }: CardProps) {
  return (
    <section
      className={`rounded-2xl border border-northbound-black80 bg-northbound-black90 shadow-[0_18px_60px_rgba(0,0,0,0.24)] transition-colors hover:border-northbound-black70 ${className}`}
    >
      {children}
    </section>
  );
}

export function CardHeader({ children, className = "" }: CardProps) {
  return <div className={`border-b border-white/10 px-5 py-4 ${className}`}>{children}</div>;
}

export function CardContent({ children, className = "" }: CardProps) {
  return <div className={`p-5 ${className}`}>{children}</div>;
}
