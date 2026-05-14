import type { SelectHTMLAttributes } from "react";

export function Select({ className = "", children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={`h-10 rounded-md border border-northbound-black80 bg-northbound-black100 px-3 text-sm text-northbound-white100 outline-none transition focus:border-northbound-white80 focus:ring-2 focus:ring-white/10 ${className}`}
      {...props}
    >
      {children}
    </select>
  );
}
