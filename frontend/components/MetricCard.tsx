"use client";

import { ReactNode } from "react";

interface MetricCardProps {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  hint?: string;
  accent?: "critical" | "warning" | "good" | "normal" | "accent";
}

const ACCENT_COLOR: Record<string, string> = {
  critical: "var(--color-critical)",
  warning:  "var(--color-warning)",
  good:     "var(--color-good)",
  normal:   "var(--color-normal)",
  accent:   "var(--color-accent)",
};

export function MetricCard({ label, value, sub, hint, accent = "normal" }: MetricCardProps) {
  return (
    <div
      className="flex flex-col gap-1 px-4 py-3 rounded-xl"
      style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}
    >
      <span className="text-xs font-medium" style={{ color: "var(--muted)" }}>{label}</span>
      <span
        className="text-2xl font-bold leading-none"
        style={{ color: ACCENT_COLOR[accent] }}
      >
        {value}
      </span>
      {sub && (
        <span className="text-xs" style={{ color: "var(--muted)" }}>{sub}</span>
      )}
      {hint && (
        <span className="text-xs mt-1 leading-snug" style={{ color: "var(--foreground)", opacity: 0.75 }}>
          {hint}
        </span>
      )}
    </div>
  );
}
