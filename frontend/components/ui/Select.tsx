import type { SelectHTMLAttributes } from "react";

export function Select({ className = "", children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={`h-10 rounded-md border border-slate-300 bg-white px-3 text-sm text-ink outline-none transition focus:border-signal focus:ring-2 focus:ring-teal-100 ${className}`}
      {...props}
    >
      {children}
    </select>
  );
}
