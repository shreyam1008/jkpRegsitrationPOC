import type { LucideIcon } from "lucide-react";
import { Search, UserPlus } from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  mobileAccess: "full" | "read-only";
}

export const NAV_ITEMS: readonly NavItem[] = [
  { to: "/", label: "Search", icon: Search, mobileAccess: "full" },
  { to: "/add", label: "Add Satsangee", icon: UserPlus, mobileAccess: "full" },
];
