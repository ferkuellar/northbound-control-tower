import type { ReactNode } from "react";

type BadgeProps = {
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
  children: ReactNode;
};

const tones = {
  neutral: "border-slate-200 bg-slate-50 text-steel",
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
  danger: "border-red-200 bg-red-50 text-risk",
  info: "border-sky-200 bg-sky-50 text-sky-700",
};

export function Badge({ tone = "neutral", children }: BadgeProps) {
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}
