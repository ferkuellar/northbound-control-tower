import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  children: ReactNode;
};

const variants = {
  primary: "border-signal bg-signal text-white hover:bg-teal-800",
  secondary: "border-slate-300 bg-white text-ink hover:bg-slate-50",
  ghost: "border-transparent bg-transparent text-steel hover:bg-slate-100 hover:text-ink",
  danger: "border-risk bg-risk text-white hover:bg-red-800",
};

export function Button({ variant = "primary", className = "", children, ...props }: ButtonProps) {
  return (
    <button
      className={`inline-flex h-10 items-center justify-center gap-2 rounded-md border px-4 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
