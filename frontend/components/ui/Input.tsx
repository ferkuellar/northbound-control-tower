import type { InputHTMLAttributes } from "react";

export function Input({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`h-10 rounded-md border border-slate-300 bg-white px-3 text-sm text-ink outline-none transition focus:border-signal focus:ring-2 focus:ring-teal-100 ${className}`}
      {...props}
    />
  );
}
