import type { ReactNode } from "react";

type BadgeProps = {
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
  children: ReactNode;
};

const tones = {
  neutral: "border-northbound-black80 bg-northbound-black100 text-northbound-white60",
  success: "border-emerald-500/30 bg-emerald-950/50 text-emerald-200",
  warning: "border-amber-500/30 bg-amber-950/50 text-amber-200",
  danger: "border-red-500/30 bg-red-950/60 text-red-200",
  info: "border-sky-500/30 bg-sky-950/50 text-sky-200",
};

export function Badge({ tone = "neutral", children }: BadgeProps) {
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}
