"use client";

import type { InsightCard } from "@/lib/api";

const CATEGORY_COLOR: Record<string, string> = {
  "흐름":       "#2563EB",
  "속도":       "#F59E0B",
  "품질":       "#059669",
  "부하":       "#EA580C",
  "예측가능성": "#7C3AED",
  "위험":       "#DC2626",
  "구조":       "#0D9488",
};

const STATUS_LABEL: Record<string, string> = {
  real:     "실측",
  approx:   "근사치",
  mock:     "수집예정",
  disabled: "비활성",
};

const STATUS_COLOR: Record<string, string> = {
  real:     "var(--color-good)",
  approx:   "var(--color-warning)",
  mock:     "var(--color-normal)",
  disabled: "var(--color-normal)",
};

const TARGET_LABEL: Record<string, string> = {
  both:     "공통",
  manager:  "중간관리자",
  decision: "의사결정",
};

interface Props {
  card: InsightCard;
  onClick?: (card: InsightCard) => void;
}

export function InsightCard({ card, onClick }: Props) {
  const catColor = CATEGORY_COLOR[card.category] ?? "var(--color-normal)";
  const isDisabled = card.zone === "disabled";

  const clickable = !isDisabled && card.data_status !== "mock";

  return (
    <div
      onClick={clickable ? () => onClick?.(card) : undefined}
      className={`rounded-2xl p-4 flex flex-col gap-3 transition-all${clickable ? " cursor-pointer hover:opacity-90" : ""}`}
      style={{
        backgroundColor: "var(--surface)",
        border: `1.5px solid ${card.alert ? "var(--color-critical)" : "var(--border)"}`,
        opacity: isDisabled ? 0.55 : 1,
      }}
    >
      {/* 헤더 */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span
            className="text-xs font-medium px-2 py-0.5 rounded-full"
            style={{ backgroundColor: catColor + "18", color: catColor }}
          >
            {card.category}
          </span>
          <span
            className="text-xs px-1.5 py-0.5 rounded-full"
            style={{ backgroundColor: "var(--background)", color: "var(--muted)", border: "1px solid var(--border)" }}
          >
            {TARGET_LABEL[card.target]}
          </span>
        </div>
        <span
          className="text-xs px-1.5 py-0.5 rounded-full shrink-0"
          style={{
            color: STATUS_COLOR[card.data_status],
            backgroundColor: STATUS_COLOR[card.data_status] + "15",
          }}
        >
          {STATUS_LABEL[card.data_status]}
        </span>
      </div>

      {/* 제목 */}
      <div>
        <div className="text-xs font-mono" style={{ color: "var(--muted)" }}>{card.id}</div>
        <div className="text-sm font-semibold mt-0.5" style={{ color: "var(--foreground)" }}>
          {card.title}
        </div>
      </div>

      {/* 핵심 지표 */}
      <div>
        <div
          className="text-2xl font-bold"
          style={{ color: card.alert ? "var(--color-critical)" : "var(--foreground)" }}
        >
          {card.primary_value}
        </div>
        <div className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
          {card.primary_label}
        </div>
      </div>

      {/* 세부 지표 */}
      {card.details.length > 0 && (
        <div
          className="flex flex-col gap-1 pt-2"
          style={{ borderTop: "1px solid var(--border)" }}
        >
          {card.details.map((d, i) => (
            <div key={i} className="flex items-center justify-between">
              <span
                className="text-xs"
                style={{ color: d.highlight ? "var(--color-warning)" : "var(--muted)" }}
              >
                {d.label}
              </span>
              <div className="flex items-center gap-1.5">
                <span
                  className="text-xs font-medium"
                  style={{ color: d.highlight ? "var(--color-warning)" : "var(--foreground)" }}
                >
                  {d.value}
                </span>
                {d.secondary && (
                  <span className="text-xs" style={{ color: "var(--muted)" }}>
                    {d.secondary}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 노트 */}
      {card.note && (
        <div
          className="text-xs rounded-lg px-2 py-1.5"
          style={{ backgroundColor: "var(--background)", color: "var(--muted)" }}
        >
          {card.note}
        </div>
      )}
    </div>
  );
}
