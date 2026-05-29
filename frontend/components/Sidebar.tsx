"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  CheckSquare,
  FolderOpen,
  GitBranch,
  FileText,
  Settings,
  Users,
  ChevronLeft,
  ChevronRight,
  LogOut,
  User,
} from "lucide-react";
import { useMe } from "@/lib/swr-hooks";
import { logout } from "@/lib/api";
import { removeToken } from "@/lib/auth";
import { NotificationBell } from "./NotificationBell";

const SIDEBAR_BG = "#16213e";
const SIDEBAR_ACTIVE_BG = "rgba(37,99,235,0.18)";
const SIDEBAR_HOVER_BG = "rgba(255,255,255,0.06)";
const SIDEBAR_TEXT = "#94a3b8";
const SIDEBAR_TEXT_ACTIVE = "#93c5fd";
const SIDEBAR_SECTION = "#475569";

interface NavItem {
  href: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  label: string;
}

const SECTIONS: { label: string; items: NavItem[] }[] = [
  {
    label: "업무",
    items: [
      { href: "/dashboard", icon: LayoutDashboard, label: "대시보드" },
    ],
  },
  {
    label: "이슈",
    items: [
      { href: "/issues", icon: CheckSquare, label: "할일관리" },
      { href: "/projects", icon: FolderOpen, label: "프로젝트" },
    ],
  },
  {
    label: "분석",
    items: [
      { href: "/flow", icon: GitBranch, label: "인사이트" },
      { href: "/reports/weekly", icon: FileText, label: "주간보고" },
    ],
  },
  {
    label: "시스템",
    items: [
      { href: "/settings", icon: Settings, label: "설정" },
    ],
  },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const { data: me } = useMe();

  const width = collapsed ? 64 : 230;

  async function handleLogout() {
    try { await logout(); } catch { /* ignore */ }
    removeToken();
    router.replace("/login");
  }

  return (
    <>
      <style>{`:root { --sidebar-width: ${width}px; }`}</style>
      <aside
        className="fixed left-0 top-0 h-screen flex flex-col z-50 transition-all duration-200"
        style={{
          width,
          backgroundColor: SIDEBAR_BG,
          borderRight: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        {/* 로고 + 토글 */}
        <div className="flex items-center justify-between px-4 py-4 shrink-0">
          {!collapsed && (
            <div className="flex items-center gap-2">
              <div
                className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold text-white"
                style={{ backgroundColor: "var(--color-accent)" }}
              >
                TI
              </div>
              <span className="font-semibold text-sm" style={{ color: "#e2e8f0" }}>
                TaskInsight
              </span>
            </div>
          )}
          {collapsed && (
            <div
              className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold text-white mx-auto"
              style={{ backgroundColor: "var(--color-accent)" }}
            >
              TI
            </div>
          )}
          {!collapsed && (
            <button
              onClick={() => setCollapsed(true)}
              className="rounded-lg p-1 transition-colors"
              style={{ color: SIDEBAR_TEXT }}
            >
              <ChevronLeft size={16} />
            </button>
          )}
        </div>

        {/* 토글 (collapsed) */}
        {collapsed && (
          <div className="flex justify-center mb-2">
            <button
              onClick={() => setCollapsed(false)}
              className="rounded-lg p-1.5 transition-colors"
              style={{ color: SIDEBAR_TEXT }}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        )}

        {/* 내비게이션 섹션들 */}
        <nav className="flex-1 overflow-y-auto px-2 pb-2">
          {[
            ...SECTIONS,
            ...(me?.is_system_admin
              ? [{ label: "관리자", items: [{ href: "/admin/users", icon: Users, label: "사용자 관리" }] }]
              : []),
          ].map((section) => (
            <div key={section.label} className="mb-1">
              {!collapsed && (
                <div
                  className="px-3 py-2 text-xs font-semibold uppercase tracking-wider"
                  style={{ color: SIDEBAR_SECTION }}
                >
                  {section.label}
                </div>
              )}
              {collapsed && <div className="py-1 border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }} />}
              {section.items.map(({ href, icon: Icon, label }) => {
                const active = pathname === href || pathname.startsWith(href + "/");
                return (
                  <Link
                    key={href}
                    href={href}
                    className="flex items-center gap-3 rounded-lg px-3 py-2 transition-colors mb-0.5"
                    style={{
                      backgroundColor: active ? SIDEBAR_ACTIVE_BG : "transparent",
                      color: active ? SIDEBAR_TEXT_ACTIVE : SIDEBAR_TEXT,
                    }}
                    onMouseEnter={(e) => {
                      if (!active) (e.currentTarget as HTMLElement).style.backgroundColor = SIDEBAR_HOVER_BG;
                    }}
                    onMouseLeave={(e) => {
                      if (!active) (e.currentTarget as HTMLElement).style.backgroundColor = "transparent";
                    }}
                    title={collapsed ? label : undefined}
                  >
                    <Icon size={16} className="shrink-0" />
                    {!collapsed && <span className="text-sm">{label}</span>}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        {/* 하단 사용자 프로필 */}
        <div
          className="shrink-0 border-t px-3 py-3"
          style={{ borderColor: "rgba(255,255,255,0.08)" }}
        >
          <div className="flex items-center gap-2.5">
            <div
              className="shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold text-white"
              style={{ backgroundColor: "var(--color-accent)" }}
            >
              {me?.display_name?.[0]?.toUpperCase() ?? <User size={14} />}
            </div>
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium truncate" style={{ color: "#e2e8f0" }}>
                  {me?.display_name ?? "..."}
                </p>
                <p className="text-xs truncate" style={{ color: SIDEBAR_TEXT }}>
                  {me?.is_system_admin ? "관리자" : "팀원"}
                </p>
              </div>
            )}
            {!collapsed && (
              <div className="flex items-center gap-1">
                <NotificationBell collapsed={false} />
                <button
                  onClick={handleLogout}
                  className="shrink-0 p-1.5 rounded-lg transition-colors"
                  style={{ color: SIDEBAR_TEXT }}
                  title="로그아웃"
                >
                  <LogOut size={14} />
                </button>
              </div>
            )}
            {collapsed && (
              <div className="absolute left-full bottom-4 ml-2">
                <NotificationBell collapsed={true} />
              </div>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}
