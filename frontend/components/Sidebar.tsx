"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  GitBranch,
  FileText,
  LayoutDashboard,
  Settings,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/flow",            icon: GitBranch,       label: "흐름 진단" },
  { href: "/reports/weekly",  icon: FileText,         label: "주간보고" },
  { href: "/dashboard",       icon: LayoutDashboard,  label: "Dashboard" },
  { href: "/settings",        icon: Settings,         label: "설정" },
] as const;

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="fixed left-0 top-0 h-screen flex flex-col items-center py-4 gap-1 z-50"
      style={{
        width: "var(--sidebar-width)",
        backgroundColor: "var(--surface)",
        borderRight: "1px solid var(--border)",
      }}
    >
      {/* 로고 */}
      <div className="mb-4 flex items-center justify-center w-10 h-10">
        <span className="text-lg font-bold" style={{ color: "var(--color-accent)" }}>
          TI
        </span>
      </div>

      {/* 내비게이션 */}
      {NAV_ITEMS.map(({ href, icon: Icon, label }) => {
        const active = pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            title={label}
            className="group flex flex-col items-center justify-center w-14 h-14 rounded-xl transition-colors"
            style={{
              backgroundColor: active ? "var(--color-accent)" : "transparent",
              color: active ? "#fff" : "var(--muted)",
            }}
          >
            <Icon size={20} />
            <span className="text-[10px] mt-0.5 leading-none">{label}</span>
          </Link>
        );
      })}
    </aside>
  );
}
