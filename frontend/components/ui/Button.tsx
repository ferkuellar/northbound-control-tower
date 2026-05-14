import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  children: ReactNode;
};

const variants = {
  primary: "border-northbound-white80 bg-northbound-white90 text-northbound-black100 hover:bg-northbound-white100",
  secondary: "border-northbound-black80 bg-northbound-black90 text-northbound-white80 hover:border-northbound-black70 hover:bg-northbound-black80",
  ghost: "border-transparent bg-transparent text-northbound-white60 hover:bg-northbound-black90 hover:text-northbound-white100",
  danger: "border-red-900/70 bg-red-950/70 text-red-100 hover:bg-red-900/80",
};

export function Button({ variant = "primary", className = "", children, ...props }: ButtonProps) {
  return (
    <button
      className={`inline-flex h-10 items-center justify-center gap-2 rounded-md border px-4 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-northbound-white80 disabled:cursor-not-allowed disabled:opacity-60 ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
