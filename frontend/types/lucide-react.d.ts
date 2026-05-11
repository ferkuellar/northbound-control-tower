declare module "lucide-react" {
  import type { FC, SVGProps } from "react";

  export type LucideIcon = FC<
    SVGProps<SVGSVGElement> & {
      size?: string | number;
      strokeWidth?: string | number;
      absoluteStrokeWidth?: boolean;
    }
  >;

  export const Activity: LucideIcon;
  export const ArrowDownRight: LucideIcon;
  export const ArrowRight: LucideIcon;
  export const ArrowUpRight: LucideIcon;
  export const BarChart3: LucideIcon;
  export const ClipboardList: LucideIcon;
  export const Database: LucideIcon;
  export const Gauge: LucideIcon;
  export const LayoutDashboard: LucideIcon;
  export const LogIn: LucideIcon;
  export const LogOut: LucideIcon;
  export const ShieldAlert: LucideIcon;
}
