"use client";

import { Folder, Calendar } from "lucide-react";

export interface FilterState {
  projectId: number | null;
  periodMonths: number;
}

interface Project {
  id: number;
  name: string;
}

interface GlobalFilterProps {
  filter: FilterState;
  onChange: (next: Partial<FilterState>) => void;
  projects?: Project[];
}

const PERIOD_OPTIONS = [
  { value: 1,   label: "최근 1개월" },
  { value: 3,   label: "최근 3개월" },
  { value: 6,   label: "최근 6개월" },
  { value: 12,  label: "최근 12개월" },
] as const;

export function GlobalFilter({ filter, onChange, projects = [] }: GlobalFilterProps) {
  return (
    <div
      className="flex items-center gap-3 px-4 py-2 rounded-lg"
      style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}
    >
      {/* 프로젝트 선택 */}
      <div className="flex items-center gap-1.5">
        <Folder size={14} style={{ color: "var(--muted)" }} />
        <select
          className="text-sm bg-transparent border-none outline-none cursor-pointer"
          style={{ color: "var(--foreground)" }}
          value={filter.projectId ?? ""}
          onChange={(e) =>
            onChange({ projectId: e.target.value ? Number(e.target.value) : null })
          }
        >
          <option value="">전체 프로젝트</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      <div style={{ width: "1px", height: "16px", backgroundColor: "var(--border)" }} />

      {/* 기간 선택 */}
      <div className="flex items-center gap-1.5">
        <Calendar size={14} style={{ color: "var(--muted)" }} />
        <select
          className="text-sm bg-transparent border-none outline-none cursor-pointer"
          style={{ color: "var(--foreground)" }}
          value={filter.periodMonths}
          onChange={(e) => onChange({ periodMonths: Number(e.target.value) })}
        >
          {PERIOD_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
