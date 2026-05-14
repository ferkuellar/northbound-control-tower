import type { InputHTMLAttributes } from "react";

export function Input({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`h-10 rounded-md border border-northbound-black80 bg-northbound-black100 px-3 text-sm text-northbound-white100 outline-none transition placeholder:text-northbound-white60 focus:border-northbound-white80 focus:ring-2 focus:ring-white/10 ${className}`}
      {...props}
    />
  );
}
